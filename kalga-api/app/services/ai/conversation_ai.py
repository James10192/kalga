"""
Orchestration de l'IA conversationnelle v2.0
============================================
Module principal qui coordonne:
- Le nouveau ConversationEngine (FSM + Mémoire + Sentiment)
- Le client DeepSeek pour les réponses avancées
- Le système de fallback pour la haute disponibilité

Architecture:
1. ConversationEngine analyse le message (intention, sentiment, contexte)
2. Si DeepSeek disponible → génère réponse IA enrichie
3. Sinon → utilise les réponses du moteur local (fallback intelligent)
"""

import re
import logging
from typing import Optional, List, Dict, Tuple

from ...database.repositories.knowledge_repo import KnowledgeBaseRepository

from .conversation_engine import (
    get_conversation_engine,
    ConversationState,
    Emotion
)
from .deepseek_client import get_deepseek_client
from .fallback_responses import FallbackResponses
from .detectors import (
    detect_delivery_request,
    detect_pickup_request,
    detect_location_request,
    detect_end_conversation,
    is_product_related_message,
    count_low_offers
)

logger = logging.getLogger("kalga.ai")


async def generate_response(
    client_message: str,
    product: Dict,
    conversation_history: List[Dict],
    current_offer: Optional[float] = None,
    conversation_status: str = "active",
    negotiation_context: Optional[Dict] = None,
    merchant_data: Optional[Dict] = None
) -> Tuple[Optional[str], Optional[float], bool, str, bool]:
    """
    Génère une réponse intelligente pour la conversation.

    Cette fonction utilise le nouveau ConversationEngine pour:
    - Analyser l'intention et le sentiment du client
    - Gérer les transitions d'état via FSM
    - Générer des réponses contextuelles et naturelles
    - Adapter les contre-offres selon l'historique du client

    Args:
        client_message: Message du client
        product: Données du produit (name, price, min_price)
        conversation_history: Historique des messages
        current_offer: Dernière offre en cours
        conversation_status: Statut actuel de la conversation
        negotiation_context: Contexte de négociation basé sur l'historique client

    Returns:
        (response_message, new_offer, deal_accepted, new_status, send_location)
    """
    # Contexte de la conversation
    is_first_message = len(conversation_history) <= 1
    product_name = product['name']
    price = product['price']
    min_price = product['min_price']

    # === PRIORITÉ 1: Conversation terminée ===
    if conversation_status == "ended":
        logger.info("Conversation terminée, pas de réponse")
        return None, current_offer, True, conversation_status, False

    # === PRIORITÉ 2: États pending (marchand prend la main) ===
    if conversation_status == "pending_pickup":
        resp, offer, accepted, status = _handle_pending_pickup(client_message, current_offer)
        # Renvoyer la localisation si le client la redemande
        resend_location = detect_location_request(client_message)
        return resp, offer, accepted, status, resend_location

    if conversation_status == "pending_delivery":
        resp, offer, accepted, status = _handle_pending_delivery(client_message, current_offer)
        return resp, offer, accepted, status, False

    # === PRIORITÉ 3: Fin de conversation explicite ===
    if detect_end_conversation(client_message) and not is_first_message:
        logger.info(f"Fin de conversation détectée: {client_message[:30]}")
        return None, current_offer, False, "ended", False

    # === PRIORITÉ 4: Message hors sujet ===
    if not is_first_message and not is_product_related_message(client_message, product_name):
        logger.info(f"Message hors sujet ignoré: {client_message[:30]}")
        return None, current_offer, False, conversation_status, False

    # === UTILISER LE NOUVEAU MOTEUR DE CONVERSATION ===
    engine = get_conversation_engine()

    # Enrichir le produit avec le contexte de négociation si disponible
    enhanced_product = dict(product)
    if negotiation_context:
        # Ajuster le prix minimum effectif selon l'historique client
        base_min_price = product['min_price']
        loyalty_discount = negotiation_context.get('loyalty_discount', 0)

        if loyalty_discount > 0 and negotiation_context.get('is_returning'):
            # Appliquer une petite réduction fidélité
            price_range = product['price'] - base_min_price
            extra_discount = price_range * (loyalty_discount / 100)
            enhanced_product['effective_min_price'] = max(
                base_min_price - extra_discount,
                base_min_price * 0.95  # Jamais plus de 5% sous le min
            )
            enhanced_product['client_style'] = negotiation_context.get('client_style')
            enhanced_product['is_returning_client'] = True
            enhanced_product['client_purchases'] = negotiation_context.get('purchase_count', 0)

            logger.info(
                f"Client fidèle ({negotiation_context.get('client_style')}): "
                f"min ajusté de {base_min_price:,.0f} à {enhanced_product['effective_min_price']:,.0f} F"
            )

    try:
        result = await engine.process_message(
            client_message=client_message,
            product=enhanced_product,
            conversation_history=conversation_history,
            current_state=conversation_status,
            current_offer=current_offer,
            merchant_data=merchant_data
        )

        # Extraire les résultats
        response = result["response"]
        new_state = result["new_state"]
        new_offer = result["new_offer"]
        deal_accepted = result["deal_accepted"]
        send_location = result["send_location"]
        debug_info = result["debug_info"]

        logger.info(
            f"Engine: state={debug_info['fsm_state']}, "
            f"intent={debug_info['intent']}, "
            f"sentiment={debug_info['sentiment']}, "
            f"intensity={debug_info['sentiment_intensity']:.2f}"
        )

        # === ESSAYER D'AMÉLIORER AVEC DEEPSEEK ===
        # Seulement si le client n'est pas trop frustré et qu'on n'est pas en état final
        # NE PAS utiliser DeepSeek quand on doit envoyer la localisation (risque de placeholder)
        # NE PAS utiliser DeepSeek quand le moteur a détecté une intention de visite (réponse contextuelle)
        # NE PAS utiliser DeepSeek pour les questions d'horaires (risque d'inventer des heures)
        has_visit_intent = debug_info.get('visit_intent', False)
        has_wrong_location = debug_info.get('wrong_location', False)
        has_status_correction = debug_info.get('status_correction', False)
        is_hours_question = _is_hours_question(client_message)

        # Guards absolus (désactivent DeepSeek inconditionnellement)
        hard_blocked = (
            debug_info['sentiment'] in ['angry'] or
            new_state in ['ended', 'completed', 'pending_delivery', 'pending_pickup'] or
            send_location or
            has_visit_intent or
            has_wrong_location or
            is_hours_question or
            has_status_correction
        )
        # Score de confiance global : DeepSeek déclenché si score > 0.4
        ai_score = _compute_ai_score(debug_info, is_first_message, len(conversation_history), response)
        should_use_ai = not hard_blocked and ai_score > 0.4
        logger.debug(f"AI score: {ai_score:.2f} → {'DeepSeek' if should_use_ai else 'FSM template'}")

        # === PALIER 2: LLM fallback pour les intentions ambiguës ===
        # Déclenché quand le moteur règle dit EXPRESS_INTEREST avec faible confiance.
        # Deux effets:
        #   a) Haute confiance (≥0.78) + ACCEPT_OFFER/SAY_GOODBYE → override état/flags
        #   b) Toute confiance (≥0.60) + autre intent → hint contextuel injecté dans DeepSeek
        llm_context_hint = None
        is_ambiguous = (
            debug_info['intent'] == 'EXPRESS_INTEREST' and
            debug_info['intent_confidence'] < 0.65 and
            not is_first_message and
            not deal_accepted and
            new_state not in ['ended', 'completed']
        )
        if is_ambiguous:
            llm_result = await _try_llm_intent_classification(
                client_message=client_message,
                product=enhanced_product,
                conversation_history=conversation_history,
            )
            if llm_result:
                llm_intent = llm_result['intent']
                llm_conf = llm_result['confidence']

                # a) Overrides d'état — haute confiance uniquement
                if llm_conf >= 0.78:
                    if llm_intent == 'ACCEPT_OFFER':
                        deal_accepted = True
                        new_state = 'agreed'
                        new_offer = new_offer or enhanced_product['price']
                        logger.info("Palier2 override: EXPRESS_INTEREST → ACCEPT_OFFER")
                    elif llm_intent == 'SAY_GOODBYE':
                        return None, current_offer, False, 'ended', False
                    elif llm_intent == 'ASK_LOCATION':
                        send_location = True

                # b) Hint contextuel pour DeepSeek (confiance ≥ 0.60)
                intent_hints = {
                    'OBJECTION_PRICE': "Le client semble trouver le prix trop élevé — réponds à son objection",
                    'PRICE_QUESTION': "Le client veut en savoir plus sur le prix ou négocier — engage la discussion",
                    'ASK_LOCATION': "Le client cherche l'adresse ou la localisation de la boutique",
                    'ACCEPT_OFFER': "Le client semble vouloir accepter — confirme l'accord et demande livraison ou pickup",
                }
                if llm_intent in intent_hints:
                    llm_context_hint = intent_hints[llm_intent]

        if should_use_ai:
            ai_response = await _try_deepseek_response(
                client_message=client_message,
                product=enhanced_product,
                conversation_history=conversation_history,
                is_first_message=is_first_message,
                debug_info=debug_info,
                negotiation_context=negotiation_context,
                merchant_data=merchant_data,
                llm_context_hint=llm_context_hint
            )

            if ai_response:
                response = ai_response
                logger.debug("Réponse DeepSeek utilisée")

        return response, new_offer, deal_accepted, new_state, send_location

    except Exception as e:
        logger.error(f"Erreur ConversationEngine: {e}")
        # Fallback sur l'ancien système
        return await _legacy_fallback(
            client_message=client_message,
            product=product,
            conversation_history=conversation_history,
            current_offer=current_offer,
            is_first_message=is_first_message
        )


async def _try_llm_intent_classification(
    client_message: str,
    product: Dict,
    conversation_history: List[Dict],
) -> Optional[Dict]:
    """
    Utilise DeepSeek en mode JSON pour affiner la classification d'intention
    quand le moteur de règles retourne EXPRESS_INTEREST avec faible confiance.

    Retourne un dict {'intent': str, 'confidence': float} ou None.

    Deux niveaux d'action:
    - Haute confiance (≥0.78) + intent actionnable → override état/flags
    - Confiance moyenne (≥0.60) → contexte hint injecté dans DeepSeek uniquement
    """
    import json as _json

    try:
        deepseek = get_deepseek_client()
        if not deepseek.api_key:
            return None

        # Contexte récent: 3 derniers échanges (6 messages max)
        recent = conversation_history[-6:] if len(conversation_history) >= 6 else conversation_history
        history_lines = []
        for msg in recent:
            role = "Client" if msg.get('is_from_client') else "Vendeur"
            history_lines.append(f"{role}: {msg.get('content', '')}")
        history_text = "\n".join(history_lines)

        price_f = f"{int(product['price']):,}".replace(",", " ")

        prompt = f"""Tu es un classificateur d'intention pour une boutique ivoirienne (Côte d'Ivoire). Analyse le DERNIER message du client dans son contexte et retourne UNIQUEMENT un JSON valide.

Produit: {product['name']} à {price_f} F CFA

Historique récent:
{history_text}

Dernier message client: "{client_message}"

Intentions possibles:
- ACCEPT_OFFER: Le client accepte le prix ou la contre-offre du vendeur (même formulé en nouchi)
- SAY_GOODBYE: Le client ne veut plus acheter, il part définitivement
- OBJECTION_PRICE: Le client trouve le prix trop cher mais reste potentiellement intéressé
- PRICE_QUESTION: Le client demande le prix, veut comparer ou ouvrir une négociation
- ASK_LOCATION: Le client veut savoir où se trouve la boutique ou demande l'adresse
- EXPRESS_INTEREST: Curiosité générale, ni oui ni non (utilise si vraiment incertain)

Retourne UNIQUEMENT ce JSON (aucun autre texte):
{{"intent": "NOM_INTENTION", "confidence": 0.0}}"""

        messages = [{"role": "user", "content": prompt}]

        result = await deepseek.chat_completion(
            messages=messages,
            max_tokens=60,
            temperature=0.05
        )

        if not result:
            return None

        # Extraire le JSON de la réponse
        json_match = re.search(r'\{[^}]+\}', result, re.DOTALL)
        if not json_match:
            return None

        data = _json.loads(json_match.group(0))
        intent_name = data.get('intent', '').strip()
        confidence = float(data.get('confidence', 0.0))

        known_intents = {'ACCEPT_OFFER', 'SAY_GOODBYE', 'OBJECTION_PRICE', 'PRICE_QUESTION', 'ASK_LOCATION'}
        if confidence >= 0.60 and intent_name in known_intents:
            logger.info(f"LLM intent: {intent_name} (conf={confidence:.2f})")
            return {'intent': intent_name, 'confidence': confidence}

        return None

    except Exception as e:
        logger.debug(f"LLM intent classification error: {e}")
        return None


async def _try_deepseek_response(
    client_message: str,
    product: Dict,
    conversation_history: List[Dict],
    is_first_message: bool,
    debug_info: Dict,
    negotiation_context: Optional[Dict] = None,
    merchant_data: Optional[Dict] = None,
    llm_context_hint: Optional[str] = None
) -> Optional[str]:
    """
    Génère une réponse via DeepSeek avec la nouvelle architecture multi-messages.

    Architecture:
      [system]    → IDENTITÉ (permanent)
      [user]      → Brief produit + few-shot examples
      [assistant] → "Compris." (ancrage)
      [user]      → Situation en cours + message client + format COMPRIS/RÉPONSE
    """
    try:
        deepseek = get_deepseek_client()

        if not deepseek.api_key:
            return None

        # Prix minimum effectif (ajusté fidélité si applicable)
        effective_min = product.get('effective_min_price', product['min_price'])

        # Adresse marchand + persona
        merchant_address = None
        merchant_persona = None
        if merchant_data:
            merchant_address = merchant_data.get('address')
            bot_tone = merchant_data.get('bot_tone')
            bot_style = merchant_data.get('bot_style')
            bot_catchphrase = merchant_data.get('bot_catchphrase')
            if any([bot_tone, bot_style, bot_catchphrase]):
                merchant_persona = {
                    'bot_tone': bot_tone or 'casual',
                    'bot_style': bot_style or 'flexible',
                    'bot_catchphrase': bot_catchphrase,
                }

        # Variantes du produit si disponibles
        variants = product.get('variants') or []

        # === RÉSUMÉ DE LA CONVERSATION ===
        conversation_summary = _build_conversation_summary(conversation_history, product)

        # === SANTÉ CONVERSATIONNELLE ===
        conversation_health = _analyze_conversation_health(
            conversation_history, client_message, product
        )
        if conversation_health["summary"]:
            logger.info(f"Santé conversation: {conversation_health['summary']}")

        # === PROFIL CLIENT (fidélité) ===
        client_profile = None
        if negotiation_context and negotiation_context.get('is_returning'):
            style = negotiation_context.get('client_style', 'normal')
            purchases = negotiation_context.get('purchase_count', 0)
            style_map = {
                'loyal': f'Client fidèle ({purchases} achats) — offre un geste commercial',
                'hard_negotiator': f'Négociateur dur ({purchases} achats) — reste ferme',
                'premium': f'Client premium ({purchases} achats) — mise sur la qualité',
                'occasional': f'Client occasionnel ({purchases} achats)'
            }
            client_profile = style_map.get(style, f'Client récurrent ({purchases} achats)')

        # === RECHERCHE DANS LA BASE DE CONNAISSANCES ===
        knowledge_context = None
        merchant_id = merchant_data.get('id') if merchant_data else None
        if merchant_id:
            try:
                kb_repo = KnowledgeBaseRepository()
                kb_results = await kb_repo.search(
                    merchant_id=merchant_id,
                    query=client_message,
                    limit=3
                )
                if kb_results:
                    knowledge_context = [
                        f"Q: {entry['question']} → R: {entry['answer']}"
                        for entry in kb_results
                    ]
                    logger.debug(f"KB: {len(kb_results)} entrée(s) trouvée(s) pour la réponse")
            except Exception as kb_err:
                logger.debug(f"KB search skipped: {kb_err}")

        # === DÉTECTION LANGUE CLIENT ===
        detected_lang = _detect_client_language(conversation_history, client_message)

        # === ASSEMBLER LES MESSAGES ===
        # Fusionner les alertes de santé + le hint LLM + la langue détectée (si présents)
        health_alerts_combined = list(conversation_health['summary']) if conversation_health['summary'] else []
        if llm_context_hint:
            health_alerts_combined.append(f"[Contexte IA] {llm_context_hint}")
        if detected_lang == 'english':
            health_alerts_combined.append(
                "[Langue client: ANGLAIS] réponds en anglais uniquement, même registre WhatsApp naturel"
            )
            logger.debug("Langue détectée: anglais → hint injecté dans DeepSeek")
        elif detected_lang == 'dioula':
            health_alerts_combined.append(
                "[Langue terrain: dioula/bambara] quelques mots dioula dans ta réponse sont appréciés"
            )
            logger.debug("Langue détectée: dioula → hint injecté dans DeepSeek")

        messages = deepseek.build_messages(
            product_name=product['name'],
            price=product['price'],
            min_price=effective_min,
            history_text=conversation_summary['history_text'],
            client_message=client_message,
            is_first_message=is_first_message,
            product_description=product.get('description'),
            variants=variants if variants else None,
            merchant_address=merchant_address,
            key_facts=conversation_summary['key_facts'],
            negotiation_stage=conversation_summary['negotiation_stage'],
            health_alerts=health_alerts_combined if health_alerts_combined else None,
            final_price_mode=debug_info.get('is_final_price_mode', False),
            client_profile=client_profile,
            knowledge_context=knowledge_context,
            merchant_persona=merchant_persona
        )

        # === CALIBRER LA TEMPÉRATURE selon le stade ===
        temperature = _calibrate_temperature(debug_info, is_first_message)

        # === APPEL API ===
        raw_response = await deepseek.chat_completion(
            messages=messages,
            temperature=temperature,
            max_tokens=300
        )

        if not raw_response:
            return None

        # === EXTRAIRE LA PARTIE RÉPONSE (format COMPRIS/RÉPONSE) ===
        response = deepseek.parse_response(raw_response)

        # === VALIDATION ===
        if _has_placeholder_text(response):
            logger.warning(f"Réponse rejetée (placeholder): {response[:80]}")
            return None

        return response

    except Exception as e:
        logger.warning(f"DeepSeek non disponible: {e}")
        return None


def _calibrate_temperature(debug_info: Dict, is_first_message: bool) -> float:
    """
    Calibre la température selon le stade de la conversation.
    - Premier contact: 0.8 (chaleureux, naturel)
    - Négociation: 0.7 (équilibré)
    - Accord/clôture: 0.5 (précis, clair)
    - Frustration/confusion: 0.6 (réfléchi)
    """
    if is_first_message:
        return 0.8

    fsm_state = debug_info.get('fsm_state', '')
    sentiment = debug_info.get('sentiment', 'neutral')

    if fsm_state in ['DEAL_AGREED', 'CHOOSING_DELIVERY', 'PENDING_PICKUP', 'PENDING_DELIVERY']:
        return 0.5
    if sentiment in ['frustrated', 'angry']:
        return 0.6
    if fsm_state in ['FINAL_OFFER']:
        return 0.5

    return 0.7


def _detect_client_language(
    conversation_history: List[Dict],
    client_message: str
) -> Optional[str]:
    """
    Détecte si le client écrit dans une langue autre que le français.
    Analyse les 8 derniers messages client + le message courant.

    Returns: 'english', 'dioula', ou None (français présumé).
    """
    client_msgs = [
        m['content'].lower() for m in conversation_history[-8:]
        if m.get('is_from_client')
    ] + [client_message.lower()]
    full_text = ' '.join(client_msgs)

    english_keywords = [
        'how much', 'how many', 'i want', 'i need', 'price',
        'delivery', 'where is', 'what is', 'do you', 'can you',
        'please', 'thank you', 'available', 'send me', 'is it',
        'i would like', 'the price', 'in stock',
    ]
    # Dioula/Bambara — mots non déjà couverts par nouchi_map
    dioula_keywords = [
        'baro', 'ka numan', 'ani sogoma', 'i ni ce',
        'ka kene', 'ka di', 'ka ca', 'seben', 'ni baara',
    ]

    eng_score = sum(1 for kw in english_keywords if kw in full_text)
    dioula_score = sum(1 for kw in dioula_keywords if kw in full_text)

    if eng_score >= 2:
        return 'english'
    if dioula_score >= 1:
        return 'dioula'
    return None


def _compute_ai_score(
    debug_info: Dict,
    is_first_message: bool,
    n_turns: int,
    fsm_response: str
) -> float:
    """
    Calcule un score de pertinence pour l'appel DeepSeek (0.0 à 1.0).
    DeepSeek est utilisé si score > 0.4.

    Facteurs positifs: ambiguïté d'intention, premier message, frustration,
                       état de négociation actif, réponse FSM trop courte.
    Facteurs négatifs: très haute confiance FSM, état final stable, conv longue.
    """
    score = 0.35  # base neutre

    conf = debug_info.get('intent_confidence', 0.7)
    if conf < 0.75:
        score += 0.30   # ambiguïté → IA utile
    if conf >= 0.90:
        score -= 0.20   # très sûr → IA moins nécessaire

    if is_first_message:
        score += 0.40   # 1er message → chaleur et naturel essentiels

    sentiment = debug_info.get('sentiment', 'neutral')
    if sentiment in ('frustrated', 'doubtful'):
        score += 0.25   # nuance émotionnelle → IA meilleure

    fsm_state = debug_info.get('fsm_state', '')
    if fsm_state in ('NEGOTIATING', 'COUNTER_OFFER', 'OBJECTION_HANDLING'):
        score += 0.20   # négociation active → IA plus pertinente
    if fsm_state in ('DEAL_AGREED', 'FINAL_OFFER', 'COMPLETED'):
        score -= 0.15   # état conclusif → template FSM suffisant

    if n_turns > 15:
        score -= 0.10   # conv longue → FSM templates plus prévisibles

    # Réponse FSM trop courte = template générique → IA pour enrichir
    if fsm_response and len(fsm_response.split()) < 6:
        score += 0.25

    return max(0.0, min(1.0, score))


def _build_conversation_summary(
    conversation_history: List[Dict],
    product: Dict
) -> Dict:
    """
    Construit un résumé structuré de la conversation pour le prompt DeepSeek.
    Extrait les faits clés: prix proposés, questions posées, thèmes abordés.
    """
    import re

    history_lines = []
    key_facts = []
    client_offers = []
    bot_offers = []
    questions_asked = []
    price = product['price']
    min_price = product['min_price']

    last_bot_message = ""
    last_client_message = ""
    unanswered_questions = []
    topics_mentioned = set()

    for i, msg in enumerate(conversation_history[-15:]):  # On prend plus de contexte
        role = "Client" if msg.get('is_from_client') else "Vendeur"
        content = msg.get('content', '')
        history_lines.append(f"{role}: {content}")

        # Extraire les faits importants des messages client
        if msg.get('is_from_client'):
            last_client_message = content
            content_lower = content.lower()

            # Prix proposés par le client
            k_match = re.search(r'(\d+)\s*k\b', content_lower)
            space_match = re.search(r'(\d{1,3}(?:\s\d{3})+)', content_lower)
            simple_match = re.search(r'\b(\d{4,})\b', content_lower)

            client_price = None
            if k_match:
                client_price = int(k_match.group(1)) * 1000
            elif space_match:
                client_price = int(space_match.group(1).replace(' ', ''))
            elif simple_match:
                client_price = int(simple_match.group(1))

            if client_price and 1000 <= client_price <= price * 2:
                client_offers.append(client_price)

            # Questions posées par le client
            if '?' in content:
                questions_asked.append(content.strip())

            # Sujets détectés
            if any(w in content_lower for w in ['livr', 'envoyer', 'expedition']):
                topics_mentioned.add('livraison')
            if any(w in content_lower for w in ['qualit', 'original', 'garanti', 'vrai', 'faux']):
                topics_mentioned.add('qualite')
            if any(w in content_lower for w in ['photo', 'image', 'voir', 'couleur']):
                topics_mentioned.add('photo')
            if any(w in content_lower for w in ['adresse', 'localisation', 'boutique', 'magasin', 'passer']):
                topics_mentioned.add('localisation')

        # Messages du bot
        else:
            last_bot_message = content
            content_lower = content.lower()
            k_match = re.search(r'(\d+)\s*k\b', content_lower)
            space_match = re.search(r'(\d{1,3}(?:\s\d{3})+)', content_lower)
            if k_match:
                bot_offers.append(int(k_match.group(1)) * 1000)
            elif space_match:
                bot_offers.append(int(space_match.group(1).replace(' ', '')))

    # === Construire les faits clés ===

    # 1. Offres client
    deal_locked_price = None  # Prix d'accord verrouillé si accord trouvé
    if client_offers:
        offers_str = ", ".join([f"{o:,} F".replace(",", " ") for o in client_offers])
        key_facts.append(f"Le client a proposé: {offers_str}")
        last_offer = client_offers[-1]
        if last_offer < min_price:
            key_facts.append(
                f"Sa dernière offre ({last_offer:,} F) est SOUS le minimum ({min_price:,} F) — ne pas accepter".replace(",", " ")
            )
        else:
            deal_locked_price = last_offer
            key_facts.append(
                f"ACCORD VERROUILLÉ A {last_offer:,} F — tu as accepté ce prix. NE PROPOSE PLUS de nouveau prix! Guide vers livraison/pickup.".replace(",", " ")
            )

    # 2. Contre-offres bot
    if bot_offers:
        # Déduire les vraies contre-offres (exclure le prix affiché initial)
        real_counters = [o for o in bot_offers if o != price]
        if real_counters:
            key_facts.append(
                f"Tu as déjà contre-proposé: {', '.join([f'{o:,} F'.replace(chr(44), ' ') for o in real_counters])}"
            )

    # 3. Dernier message du bot (pour ne pas répéter)
    if last_bot_message:
        key_facts.append(f"Ta dernière réponse était: \"{last_bot_message[:80]}{'...' if len(last_bot_message) > 80 else ''}\"")

    # 4. Questions sans réponse (multi-tours)
    # Une question est "sans réponse" si c'est la dernière question du client
    # et que le bot n'a pas répondu après (= c'est le message actuel)
    if questions_asked:
        # La question la plus récente du client qui n'a pas eu de réponse bot après
        # Si le dernier message dans history est du client avec une question, c'est sans réponse
        last_msgs = conversation_history[-3:] if len(conversation_history) >= 3 else conversation_history
        client_question_pending = None
        for msg in reversed(last_msgs):
            if msg.get('is_from_client') and '?' in msg.get('content', ''):
                client_question_pending = msg['content'].strip()
                break
            elif not msg.get('is_from_client'):
                break  # Le bot a déjà répondu après la dernière question
        if client_question_pending:
            key_facts.append(f"QUESTION EN ATTENTE de réponse: \"{client_question_pending}\"")

    # 5. Sujets déjà abordés (pour ne pas répéter)
    if topics_mentioned:
        key_facts.append(f"Sujets déjà discutés: {', '.join(topics_mentioned)} — évite de les rabâcher sauf si le client insiste")

    # === Stade de la négociation ===
    n_turns = len(conversation_history)
    if n_turns <= 1:
        negotiation_stage = "DEBUT — premier contact avec le client"
    elif n_turns <= 3:
        negotiation_stage = "EXPLORATION — le client decouvre le produit"
    elif not client_offers:
        negotiation_stage = "DISCUSSION — pas encore d offre de prix"
    elif client_offers and min(client_offers) < min_price * 0.8:
        negotiation_stage = "NEGOCIATION SERREE — le client pousse fort, offres tres basses"
    elif deal_locked_price:
        negotiation_stage = f"ACCORD VERROUILLE A {int(deal_locked_price):,} F — guide vers livraison ou pickup, NE NEGOCIEZ PLUS".replace(",", " ")
    elif client_offers:
        negotiation_stage = "NEGOCIATION EN COURS — des offres ont ete echangees"
    else:
        negotiation_stage = "CONVERSATION EN COURS"

    # === Compression pour conversations longues (> 20 messages) ===
    # Les key_facts (offres, sujets) sont déjà extraits et passés séparément à DeepSeek.
    # On peut donc condenser history_text sans perdre d'information critique.
    if len(conversation_history) > 20:
        old_msgs = conversation_history[:-8]
        recent_msgs = conversation_history[-8:]

        # Extraire les faits de la partie ancienne pour le résumé
        old_offers = []
        old_topics = set()
        for msg in old_msgs:
            c = msg.get('content', '')
            cl = c.lower()
            if msg.get('is_from_client'):
                m = re.search(r'\b(\d{4,})\b', cl)
                if m:
                    p = int(m.group(1))
                    if 1000 <= p <= price * 2:
                        old_offers.append(p)
                if any(w in cl for w in ['livr', 'envoyer', 'expedition']):
                    old_topics.add('livraison')
                if any(w in cl for w in ['qualit', 'original', 'garanti']):
                    old_topics.add('qualité')
                if any(w in cl for w in ['photo', 'image', 'couleur']):
                    old_topics.add('photo')
                if any(w in cl for w in ['adresse', 'localisation', 'boutique', 'magasin']):
                    old_topics.add('localisation')

        old_summary = [f"[RÉSUMÉ — {len(old_msgs)} messages précédents condensés]"]
        if old_offers:
            old_summary.append(f"  • Offres passées: {', '.join([str(o) + ' F' for o in old_offers])}")
        if old_topics:
            old_summary.append(f"  • Sujets déjà abordés: {', '.join(old_topics)}")
        old_summary.append("[Suite — 8 derniers messages en détail]")

        recent_lines = [
            f"{'Client' if m.get('is_from_client') else 'Vendeur'}: {m.get('content', '')}"
            for m in recent_msgs
        ]
        final_history_lines = old_summary + recent_lines
    else:
        final_history_lines = history_lines

    return {
        "history_text": "\n".join(final_history_lines),
        "key_facts": key_facts,
        "negotiation_stage": negotiation_stage,
        "client_offers": client_offers,
        "bot_offers": bot_offers,
        "n_turns": n_turns,
        "last_bot_message": last_bot_message,
        "topics_mentioned": list(topics_mentioned),
        "deal_locked_price": deal_locked_price
    }


def _build_user_prompt(
    client_message: str,
    debug_info: Dict,
    negotiation_context: Optional[Dict],
    conversation_summary: Dict,
    conversation_health: Optional[Dict] = None
) -> str:
    """
    Construit le prompt utilisateur enrichi avec tout le contexte disponible.
    """
    lines = [f'Le client dit: "{client_message}"']

    # --- Contexte de la négociation (faits extraits) ---
    key_facts = conversation_summary.get('key_facts', [])
    if key_facts:
        lines.append("\n📊 CONTEXTE DE LA NÉGOCIATION:")
        for fact in key_facts:
            lines.append(f"  • {fact}")

    # --- Stade actuel ---
    stage = conversation_summary.get('negotiation_stage', '')
    if stage:
        lines.append(f"\n🎯 STADE: {stage}")

    # --- État FSM (en français lisible) ---
    fsm_state = debug_info.get('fsm_state', '')
    fsm_labels = {
        'PRICE_PRESENTED': 'Prix présenté, client réfléchit',
        'NEGOTIATING': 'Négociation en cours',
        'COUNTER_OFFER': 'Contre-offre proposée',
        'FINAL_OFFER': 'Dernier prix proposé',
        'DEAL_AGREED': 'Accord trouvé',
        'OBJECTION_HANDLING': 'Le client a une objection',
        'FRUSTRATED_CLIENT': 'Client frustré — mode empathie',
        'COOLING_OFF': 'Client veut réfléchir',
    }
    if fsm_state in fsm_labels:
        lines.append(f"📍 SITUATION: {fsm_labels[fsm_state]}")

    # --- Profil client (historique cross-conversations) ---
    if negotiation_context and negotiation_context.get('is_returning'):
        client_style = negotiation_context.get('client_style', 'normal')
        purchases = negotiation_context.get('purchase_count', 0)
        recommendation = negotiation_context.get('recommendation', '')

        lines.append(f"\n👤 PROFIL CLIENT (historique):")
        lines.append(f"  • Client récurrent — {purchases} achat(s) précédent(s)")

        style_labels = {
            'loyal': '💚 Client fidèle — offre-lui un geste commercial rapidement',
            'hard_negotiator': '⚠️ Négociateur dur — reste ferme, propose des paliers progressifs',
            'premium': '✨ Client premium — peu de négociation, mise sur la qualité',
            'occasional': '🔄 Client occasionnel — traite normalement'
        }
        style_text = style_labels.get(client_style, f'Style: {client_style}')
        lines.append(f"  • {style_text}")

        if recommendation:
            lines.append(f"  • Recommandation: {recommendation}")

    # --- Sentiment détecté ---
    sentiment = debug_info.get('sentiment', 'neutral')
    intensity = debug_info.get('sentiment_intensity', 0.3)
    intent = debug_info.get('intent', '')

    sentiment_labels = {
        'frustrated': f'Client FRUSTRE (intensite: {intensity:.0%}) — reste calme et empathique!',
        'angry': f'Client EN COLERE (intensite: {intensity:.0%}) — desescalade immediate!',
        'doubtful': 'Client qui doute — rassure-le sur la qualite et le serieux',
        'impatient': 'Client impatient — va droit au but, pas de blabla',
        'interested': 'Client interesse — c est le bon moment pour conclure',
        'happy': 'Client content — ambiance positive, profite pour conclure',
    }
    if sentiment in sentiment_labels:
        lines.append(f"\nEMOTION DETECTEE: {sentiment_labels[sentiment]}")

    # --- Détection d'ambiguïté (Phase 4) ---
    ambiguity = _detect_ambiguity(client_message, debug_info)
    if ambiguity:
        lines.append(f"\nMESSAGE AMBIGU: {ambiguity}")
        lines.append("Si tu n es pas sur de l intention, pose une question courte de clarification.")

    # --- Santé conversationnelle ---
    if conversation_health and conversation_health.get("summary"):
        lines.append("\n⚠️ ALERTE CONTEXTE:")
        for signal in conversation_health["summary"]:
            lines.append(f"  ⚡ {signal}")
        lines.append(
            "\nACTION REQUISE: Tiens compte de ces alertes pour adapter ta réponse. "
            "Ne répète pas ce que tu as déjà dit. Lis vraiment ce que le client exprime."
        )

    return "\n".join(lines)


def _analyze_conversation_health(
    conversation_history: List[Dict],
    client_message: str,
    product: Dict
) -> Dict:
    """
    Analyse la dynamique de la conversation pour détecter les signaux de perte de contexte.

    Retourne un rapport de "santé" conversationnelle:
    - is_looping: le bot répète le même contenu
    - unanswered_question: le bot n'a pas répondu à une vraie question
    - bot_ignored_client: le client a été ignoré dans les derniers échanges
    - unknown_expression: message court sans intention claire détectable
    - conversation_stuck: la conversation n'avance pas
    """
    import re

    health = {
        "is_looping": False,
        "loop_content": None,
        "unanswered_question": False,
        "last_unanswered": None,
        "bot_ignored_client": False,
        "unknown_expression": False,
        "conversation_stuck": False,
        "stuck_turns": 0,
        "summary": []
    }

    # Détection expression inconnue fonctionne dès le 1er message client
    msg_clean = client_message.strip()
    has_price = bool(re.search(r'\d{3,}', msg_clean))
    is_very_short = len(msg_clean) < 15
    no_clear_intent = not any(w in msg_clean.lower() for w in [
        'oui', 'non', 'ok', 'merci', 'livr', 'viens', 'passe', 'adresse',
        'photo', 'cher', 'prix', 'combien', 'deal', 'accord', 'dispo',
        'bonjour', 'salut', 'bonsoir', 'hello', 'bye', 'merci'
    ])
    if is_very_short and not has_price and no_clear_intent and len(conversation_history) >= 1:
        health["unknown_expression"] = True
        health["summary"].append(
            f"EXPRESSION INCERTAINE: \"{msg_clean}\" — si tu ne comprends pas ce mot ou cette expression, "
            f"dis-le honnêtement et demande au client ce qu'il veut dire"
        )

    if len(conversation_history) < 2:
        return health

    # Récupérer les derniers messages
    recent = conversation_history[-6:] if len(conversation_history) >= 6 else conversation_history
    bot_messages = [m['content'] for m in recent if not m.get('is_from_client')]
    client_messages = [m['content'] for m in recent if m.get('is_from_client')]

    price = product['price']
    price_str_variants = [
        f"{int(price):,}".replace(",", " "),
        f"{int(price):,}".replace(",", "."),
        str(int(price)),
    ]

    # --- Détection de boucle ---
    # Le bot répète le même prix ou le même contenu clé sur 2+ messages consécutifs
    if len(bot_messages) >= 2:
        for variant in price_str_variants:
            occurrences = sum(1 for bm in bot_messages if variant in bm)
            if occurrences >= 2:
                health["is_looping"] = True
                health["loop_content"] = f"le prix {variant} F répété {occurrences} fois"
                health["summary"].append(
                    f"BOUCLE DÉTECTÉE: tu as répété {variant} F dans {occurrences} de tes derniers messages — ARRÊTE de répéter ce chiffre"
                )
                break

        # Vérifier aussi si deux messages bot consécutifs sont très similaires (>70% de mots communs)
        if len(bot_messages) >= 2 and not health["is_looping"]:
            last_two = bot_messages[-2:]
            words_a = set(last_two[0].lower().split())
            words_b = set(last_two[1].lower().split())
            if words_a and words_b:
                overlap = len(words_a & words_b) / min(len(words_a), len(words_b))
                if overlap > 0.7 and len(words_a) > 3:
                    health["is_looping"] = True
                    health["loop_content"] = "messages très similaires"
                    health["summary"].append(
                        "BOUCLE DÉTECTÉE: tes deux derniers messages se ressemblent trop — varie ta réponse"
                    )

    # --- Détection de question sans réponse ---
    # Regarder si le client a posé une vraie question (? ou question implicite)
    # dans les 2 derniers échanges sans que le bot y réponde directement
    if len(recent) >= 3:
        # Chercher la dernière question client AVANT le dernier message bot
        last_bot_idx = None
        for i in range(len(recent) - 1, -1, -1):
            if not recent[i].get('is_from_client'):
                last_bot_idx = i
                break

        if last_bot_idx is not None and last_bot_idx > 0:
            # Messages client avant le dernier message bot
            client_before_last_bot = [
                m for m in recent[:last_bot_idx] if m.get('is_from_client')
            ]
            if client_before_last_bot:
                last_client_q = client_before_last_bot[-1]['content']
                # Question explicite avec ?
                if '?' in last_client_q:
                    last_bot_content = recent[last_bot_idx]['content'].lower()
                    # Le bot a-t-il répondu à la question?
                    # Si sa réponse est courte et contient le prix → il a esquivé, pas répondu
                    acknowledgment_words = ['pardon', 'excuse', 'comprends', 'entends', 'sorry', 'desole']
                    has_acknowledgment = any(w in last_bot_content for w in acknowledgment_words)
                    seems_ignored = (
                        len(last_bot_content.split()) < 15 and
                        any(v in last_bot_content for v in price_str_variants) and
                        not has_acknowledgment
                    )
                    if seems_ignored:
                        health["unanswered_question"] = True
                        health["last_unanswered"] = last_client_q
                        health["summary"].append(
                            f"QUESTION IGNORÉE: le client a demandé \"{last_client_q[:60]}\" — tu as répondu avec le prix au lieu de répondre à sa question"
                        )

    # --- Détection question répétée ---
    # Le client pose la même question 2 fois → le bot ne l'a jamais traitée
    if len(recent) >= 4:
        client_questions = [
            m['content'] for m in recent if m.get('is_from_client') and '?' in m.get('content', '')
        ]
        if len(client_questions) >= 2:
            # Comparer les deux dernières questions par chevauchement de mots
            q1_words = set(client_questions[-2].lower().split())
            q2_words = set(client_questions[-1].lower().split())
            # Supprimer les mots courants pour ne garder que les mots significatifs
            common_stops = {'je', 'tu', 'il', 'on', 'le', 'la', 'les', 'de', 'du', 'et', 'en', 'un', 'une', 'est'}
            q1_sig = q1_words - common_stops
            q2_sig = q2_words - common_stops
            if q1_sig and q2_sig:
                overlap = len(q1_sig & q2_sig) / min(len(q1_sig), len(q2_sig))
                if overlap >= 0.5 and not health["unanswered_question"]:
                    health["unanswered_question"] = True
                    health["last_unanswered"] = client_questions[-1]
                    health["summary"].append(
                        f"QUESTION RÉPÉTÉE: le client a reposé la même question \"{client_questions[-1][:50]}\" — "
                        f"tu ne l'as pas encore répondue, réponds-y maintenant"
                    )

    # --- Détection question actuelle sans réponse prévisible ---
    # Si le message courant est une question et que le dernier message bot
    # ne contenait aucun mot-clé de la question → risque d'ignorer encore
    if '?' in client_message and len(recent) >= 2 and not health["unanswered_question"]:
        last_bot_msgs = [m['content'] for m in recent if not m.get('is_from_client')]
        if last_bot_msgs:
            last_bot = last_bot_msgs[-1].lower()
            # Mots significatifs de la question actuelle
            q_words = set(re.sub(r'[^\w\s]', ' ', client_message.lower()).split())
            sig_q_words = {w for w in q_words if len(w) >= 4 and w not in {
                'vous', 'votre', 'quel', 'quelle', 'comment', 'combien', 'pouvez',
                'faire', 'avez', 'avec', 'pour', 'dans', 'cette', 'aussi'
            }}
            # Si aucun mot significatif de la question n'apparaît dans la dernière réponse bot
            # ET que la réponse bot contient le prix → signal fort d'esquive
            bot_addresses_question = any(w in last_bot for w in sig_q_words)
            bot_has_only_price = any(v in last_bot for v in price_str_variants)
            if not bot_addresses_question and bot_has_only_price and len(sig_q_words) >= 2:
                health["summary"].append(
                    f"ALERTE CONTEXTE: ta dernière réponse n'a pas traité la question du client. "
                    f"Réponds d'abord à \"{client_message[:50]}\" avant de parler du prix."
                )


    # --- Détection conversation bloquée ---
    # Si les 3+ derniers messages client ne contiennent pas d'offre et que le bot répète le prix
    if len(client_messages) >= 3 and not any(
        re.search(r'\d{4,}', m) for m in client_messages[-3:]
    ):
        if health["is_looping"]:
            health["conversation_stuck"] = True
            health["stuck_turns"] = len(client_messages)
            health["summary"].append(
                "CONVERSATION BLOQUÉE: le client ne fait pas d'offre et tu répètes le prix — "
                "change d'approche: pose une vraie question ou propose autre chose"
            )

    return health


def _detect_ambiguity(client_message: str, debug_info: Dict) -> Optional[str]:
    """
    Détecte si le message client est ambigu et nécessite une clarification.
    Retourne une description de l'ambiguïté, ou None si le message est clair.
    """
    msg = client_message.lower().strip()
    intent = debug_info.get('intent', '')
    confidence = debug_info.get('intent_confidence', 1.0)

    # Ambiguïtés connues
    ambiguities = [
        # "c'est le dernier?" → dernier prix ou dernier produit en stock?
        {
            'patterns': ["c'est le dernier", "c est le dernier", "dernier ?", "dernier?"],
            'description': "\"dernier\" peut vouloir dire dernier prix OR dernier produit en stock"
        },
        # "tu peux faire mieux?" → invitation à négocier, pas une offre de prix
        {
            'patterns': ["tu peux faire mieux", "vous pouvez faire mieux", "mieux que ca", "mieux que ça"],
            'description': "invitation a negocier, pas une offre precise — propose un chiffre ou demande leur budget"
        },
        # "bon" seul → accord ou simple commentaire?
        {
            'patterns': [],
            'exact': ['bon', 'boh', 'bof'],
            'description': "\"bon\" peut etre un accord OR un commentaire neutre — verifie le contexte"
        },
        # "c'est tout?" → satisfait ou demande d'autre chose?
        {
            'patterns': ["c'est tout", "c est tout", "c'est ca", "c est ca"],
            'description': "peut vouloir dire \"je prends\" OR \"c est tout ce que tu proposes?\""
        },
    ]

    for amb in ambiguities:
        # Vérification par patterns
        if any(p in msg for p in amb.get('patterns', [])):
            return amb['description']
        # Vérification exacte
        if msg in amb.get('exact', []):
            return amb['description']

    # Confiance faible du moteur = ambiguïté probable
    if confidence < 0.55 and len(msg) < 20:
        return f"message court et ambigu (confiance intent: {confidence:.0%}) — demande clarification si necessaire"

    return None


def _is_hours_question(message: str) -> bool:
    """
    Détecte si le client demande les horaires d'ouverture.
    Ces questions sont gérées sans DeepSeek (réponse fixe) pour éviter les inventions.
    Utilise des patterns précis pour éviter les faux positifs.
    """
    msg = message.lower()
    # Patterns précis liés aux horaires d'ouverture (pas "à l'heure" ou "tout à l'heure")
    hours_patterns = [
        'horaire', 'ouverture', 'fermeture',
        'quelle heure', "jusqu'a quelle heure", 'a partir de quelle heure',
        'de quel heure', 'ouvert quand', 'quand vous ouvrez', 'quand vous fermez',
        'vous ouvrez a', 'vous fermez a', 'vous etes ouvert',
        'tu es ouvert', 'c est ouvert', 'vous ouvrez', 'vous fermez',
        'ouvert jusqu', 'ferme quand', 'ouvert de',
    ]
    return any(p in msg for p in hours_patterns)


def _has_placeholder_text(text: str) -> bool:
    """Détecte les placeholders/texte fictif dans une réponse DeepSeek"""
    placeholder_patterns = [
        '[insérer', '[inserer', '[adresse', '[horaire', '[heure',
        '[lieu', '[localisation', '[nom du', '[votre', '[ton',
        '[insert', '[address', '[location', '[hours',
        'insérer l\'adresse', 'inserer l\'adresse',
        'insérer ici', 'inserer ici',
    ]
    text_lower = text.lower()
    if any(p in text_lower for p in placeholder_patterns):
        return True

    # Détecter les horaires inventés (patterns: "ouvert de Xh à Yh", "X h à Y h")
    import re
    invented_hours_patterns = [
        r'ouvert\s+de\s+\d+h',
        r'ouverts?\s+de\s+\d+',
        r'ouverture\s+\d+h',
        r'de\s+\d+h\s+[àa]\s+\d+h',
        r'\d+h\s*[àa]\s*\d+h',
        r'ferme\s+[àa]\s+\d+h',
    ]
    for pattern in invented_hours_patterns:
        if re.search(pattern, text_lower):
            return True

    return False


async def _legacy_fallback(
    client_message: str,
    product: Dict,
    conversation_history: List[Dict],
    current_offer: Optional[float],
    is_first_message: bool
) -> Tuple[str, Optional[float], bool, str, bool]:
    """Fallback sur l'ancien système de réponses"""
    logger.warning("Utilisation du fallback legacy")

    low_offers_count = count_low_offers(conversation_history, product['min_price'])

    response, offer, accepted, status = FallbackResponses.generate_response(
        client_message=client_message,
        product_name=product['name'],
        price=product['price'],
        min_price=product['min_price'],
        current_offer=current_offer,
        is_first_message=is_first_message,
        low_offers_count=low_offers_count,
        product_description=product.get('description')
    )

    # Détecter si le client demande la localisation
    send_location = detect_location_request(client_message)
    return response, offer, accepted, status, send_location


def _handle_pending_pickup(
    client_message: str,
    current_offer: Optional[float]
) -> Tuple[str, Optional[float], bool, str]:
    """Gère les messages quand le client attend l'adresse"""
    import random
    msg_lower = client_message.lower()

    # Redemande l'adresse (vérifier AVANT les confirmations car "reçu" est ambigu)
    if detect_location_request(msg_lower):
        return "Je te renvoie la localisation tout de suite !", current_offer, True, "pending_pickup"

    # Client confirme/remercie
    if any(kw in msg_lower for kw in ['ok', 'oui', 'merci', 'd\'accord', 'attends', 'j\'attends', 'vu', 'bien', 'super', 'parfait']):
        responses = [
            "A tout a l'heure alors !",
            "On t'attend !",
            "Parfait, a bientot !"
        ]
        return random.choice(responses), current_offer, True, "pending_pickup"

    # Autre question
    return "Pour plus d'infos, le vendeur te repond directement !", current_offer, True, "pending_pickup"


def _handle_pending_delivery(
    client_message: str,
    current_offer: Optional[float]
) -> Tuple[str, Optional[float], bool, str]:
    """Gère les messages quand le client attend la livraison"""
    import random
    msg_lower = client_message.lower()

    if any(kw in msg_lower for kw in ['ok', 'oui', 'merci', 'd\'accord', 'attends', 'j\'attends', 'bien', 'super', 'parfait']):
        responses = [
            "Parfait ! Le vendeur te contacte pour la livraison.",
            "C'est note, on te rappelle tres vite !",
            "Top ! Tu seras contacte rapidement."
        ]
        return random.choice(responses), current_offer, True, "pending_delivery"

    return "Le vendeur te contacte pour finaliser la livraison !", current_offer, True, "pending_delivery"


# Alias public pour import depuis chat_service (boucle d'apprentissage autonome)
analyze_conversation_health = _analyze_conversation_health
