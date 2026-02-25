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

import json
import logging
from typing import Optional, List, Dict, Tuple

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
from .memory import stm as stm_module
from .tools import TOOLS, TOOL_NAMES

# Préfixe interne pour transporter un tool_call dans le tuple de retour
_TOOL_PREFIX = "__tool__:"

logger = logging.getLogger("kalga.ai")


async def generate_response(
    client_message: str,
    product: Dict,
    conversation_history: List[Dict],
    current_offer: Optional[float] = None,
    conversation_status: str = "active",
    negotiation_context: Optional[Dict] = None,
    episodic_context: Optional[str] = None
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
            current_offer=current_offer
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
        should_use_ai = (
            debug_info['sentiment'] not in ['angry'] and
            new_state not in ['ended', 'completed', 'pending_delivery', 'pending_pickup'] and
            not send_location
        )

        if should_use_ai:
            ai_response = await _try_deepseek_response(
                client_message=client_message,
                product=enhanced_product,
                conversation_history=conversation_history,
                is_first_message=is_first_message,
                debug_info=debug_info,
                negotiation_context=negotiation_context,
                episodic_context=episodic_context
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


def _extract_negotiation_state(history: List[Dict], min_price: float) -> tuple:
    """
    Extrait last_bot_offer et counter_count depuis l'historique.
    Retourne (last_bot_offer, counter_count).
    """
    import re as _re
    last_bot_offer = None
    counter_count = 0
    for msg in history:
        if not msg.get("is_from_client"):
            content = msg.get("content", "")
            # Détecter les messages de contre-offre bot (contenant un prix en FCFA)
            m = _re.search(r"(\d[\d\s]*(?:000|k))\s*(?:F|FCFA|francs)?", content, _re.IGNORECASE)
            if m:
                raw = m.group(1).replace(" ", "").lower().replace("k", "000")
                try:
                    val = float(raw)
                    if min_price * 0.8 <= val <= 999_999:
                        last_bot_offer = val
                        counter_count += 1
                except ValueError:
                    pass
    return last_bot_offer, counter_count


async def _try_deepseek_response(
    client_message: str,
    product: Dict,
    conversation_history: List[Dict],
    is_first_message: bool,
    debug_info: Dict,
    negotiation_context: Optional[Dict] = None,
    episodic_context: Optional[str] = None
) -> Optional[str]:
    """
    Tente de générer une réponse via DeepSeek (mode agentique).
    L'IA choisit elle-même le tool à appeler ou génère un texte libre.

    Retourne :
    - Une chaîne texte normale (réponse free-text)
    - Un marqueur "__tool__:<name>:<json_args>" si l'IA a choisi un tool
    - None en cas d'erreur ou d'indisponibilité
    """
    try:
        deepseek = get_deepseek_client()

        if not deepseek.api_key:
            return None

        # STM : compression de contexte si historique long
        context_summary, recent_msgs = await stm_module.build_context(
            history=conversation_history,
            deepseek_client=deepseek
        )

        # Construire l'historique formaté (via STM)
        history_text = stm_module.format_for_prompt(context_summary, recent_msgs)

        # Utiliser le min_price effectif si disponible (ajusté pour fidélité)
        effective_min = product.get('effective_min_price', product['min_price'])

        # Extraire les infos de négociation pour éviter les répétitions de prix
        last_bot_offer, counter_count = _extract_negotiation_state(
            conversation_history, effective_min
        )

        # Construire le prompt système enrichi (avec résumé STM si disponible)
        system_prompt = deepseek.build_negotiation_prompt(
            product_name=product['name'],
            price=product['price'],
            min_price=effective_min,
            history_text=history_text,
            low_offers_count=debug_info.get('low_offers_count', 0),
            final_price_mode=debug_info.get('is_final_price_mode', False),
            conversation_status=debug_info.get('fsm_state', 'NEGOTIATING'),
            is_first_message=is_first_message,
            product_description=product.get('description'),
            context_summary=context_summary,
            last_bot_offer=last_bot_offer,
            counter_count=counter_count
        )

        # Enrichir le prompt utilisateur avec le contexte détecté
        user_prompt = f'Le client dit: "{client_message}"'

        # Injecter la mémoire épisodique (contexte inter-sessions)
        if episodic_context:
            user_prompt += f"\n\n{episodic_context}"

        # Ajouter le contexte de l'historique client
        if negotiation_context and negotiation_context.get('is_returning'):
            client_style = negotiation_context.get('client_style', 'normal')
            purchases = negotiation_context.get('purchase_count', 0)
            recommendation = negotiation_context.get('recommendation', '')

            user_prompt += f"\n\n👤 PROFIL CLIENT:"
            user_prompt += f"\n- Client récurrent ({purchases} achats précédents)"
            user_prompt += f"\n- Style: {client_style}"
            user_prompt += f"\n- Recommandation: {recommendation}"

            if client_style == 'loyal':
                user_prompt += "\n💚 Client fidèle! Sois reconnaissant et offre un bon prix rapidement."
            elif client_style == 'hard_negotiator':
                user_prompt += "\n⚠️ Négociateur dur. Reste ferme mais propose des paliers progressifs."
            elif client_style == 'premium':
                user_prompt += "\n✨ Client premium. Peu de négociation nécessaire, mise sur la qualité."

        # Ajouter les informations de sentiment
        sentiment = debug_info.get('sentiment', 'neutral')
        intensity = debug_info.get('sentiment_intensity', 0.3)

        if sentiment == 'frustrated' or sentiment == 'angry':
            user_prompt += f"\n\n⚠️ ATTENTION: Client {sentiment} (intensité: {intensity:.0%}). Reste calme et empathique!"

        if sentiment == 'doubtful':
            user_prompt += "\n\n📌 Le client a des doutes. Rassure-le sur la qualité et le sérieux."

        # Appel agentique — DeepSeek décide texte ou tool
        result = await deepseek.agentic_completion(system_prompt, user_prompt, TOOLS)

        if not result:
            return None

        if result["type"] == "tool_call":
            name = result["name"]
            args = result["args"]
            # Valider que le tool est connu
            if name not in TOOL_NAMES:
                logger.warning(f"Tool inconnu retourné par DeepSeek: {name}")
                return None
            # Encoder le tool_call comme marqueur dans la string de retour
            return f"{_TOOL_PREFIX}{name}:{json.dumps(args, ensure_ascii=False)}"

        # Réponse texte libre
        content = result.get("content", "")
        if content and _has_placeholder_text(content):
            logger.warning(f"DeepSeek text rejeté (placeholder): {content[:80]}")
            return None

        return content or None

    except Exception as e:
        logger.warning(f"DeepSeek non disponible: {e}")
        return None


def is_tool_call(response: str) -> bool:
    """Vérifie si une réponse encode un tool_call."""
    return bool(response and response.startswith(_TOOL_PREFIX))


def parse_tool_call(response: str) -> Optional[Dict]:
    """
    Parse un marqueur tool_call encodé.
    Retourne {"name": str, "args": dict} ou None.
    """
    if not is_tool_call(response):
        return None
    try:
        payload = response[len(_TOOL_PREFIX):]
        name, _, args_json = payload.partition(":")
        args = json.loads(args_json) if args_json else {}
        return {"name": name, "args": args}
    except Exception:
        return None


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
    return any(p in text_lower for p in placeholder_patterns)


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
