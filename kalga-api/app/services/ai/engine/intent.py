"""
KALGA Conversation Engine — Intent Extraction
===============================================
Extracteur d'intentions sophistiqué.
"""

import re
import unicodedata
import logging
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

from .states import ConversationState, ConversationEvent
from .memory import ConversationMemory

logger = logging.getLogger("kalga.conversation_engine")


@dataclass
class Intent:
    """Intention détectée dans un message"""
    event: ConversationEvent
    confidence: float
    extracted_data: Dict[str, Any] = field(default_factory=dict)


class IntentExtractor:
    """
    Extracteur d'intentions sophistiqué.
    Analyse les messages pour déterminer l'intention du client.
    """

    def extract(self, message: str, context: ConversationMemory, current_state: ConversationState = None, merchant_data: Dict = None, last_bot_message: str = None, intent_history: List[str] = None) -> Intent:
        """Extrait l'intention principale du message"""
        msg_lower = self._normalize_message(message.lower())

        # -1. PRIORITÉ ABSOLUE: Le client conteste un achat prématurément déclaré
        # "j'ai rien acheté", "j'ai pas commandé", etc.
        if self._is_status_correction(msg_lower):
            return Intent(
                event=ConversationEvent.EXPRESS_FRUSTRATION,
                confidence=0.95,
                extracted_data={"status_correction": True}
            )

        # -0.5 GOODBYE HAUTE PRIORITÉ: dépasse localisation, objections et livraison
        # ι08: "au revoir et envoie la position quand même" → goodbye gagne (pas ASK_LOCATION)
        # ζ03: "ça dégage ici trop cher" → goodbye gagne (pas OBJECTION_PRICE)
        high_priority_goodbyes = ['au revoir', 'ca degage', 'je degage']
        if any(hpg in msg_lower for hpg in high_priority_goodbyes):
            return Intent(
                event=ConversationEvent.SAY_GOODBYE,
                confidence=0.9,
                extracted_data={}
            )

        # 0.2 CONTEXTE BOT: résolution d'intention basée sur la dernière action du bot
        # "bon" après une contre-offre → ACCEPT_OFFER et non EXPRESS_INTEREST
        # "pickup" après "livraison ou pickup ?" → CHOOSE_PICKUP
        if last_bot_message:
            context_intent = self._resolve_with_bot_context(msg_lower, last_bot_message)
            if context_intent:
                return context_intent

        # 0. PRIORITÉ MAXIMALE: Vérifier pickup/localisation AVANT l'acceptation
        # Car "oui oui mais je veux passer recuperer" n'est PAS une acceptation,
        # c'est un choix de pickup. Fonctionne depuis tout état de négociation.
        # MAIS PAS au premier message (le client explore, pas encore d'accord)
        negotiation_states = {
            ConversationState.DEAL_AGREED,
            ConversationState.PRICE_PRESENTED,
            ConversationState.NEGOTIATING,
            ConversationState.COUNTER_OFFER,
            ConversationState.FINAL_OFFER,
        }
        has_enough_context = context.total_messages > 1  # Pas au premier message
        # Pickup/delivery seulement après accord ou négociation avancée
        # Pas depuis PRICE_PRESENTED (le client n'a pas encore négocié)
        pickup_ready_states = {
            ConversationState.DEAL_AGREED,
            ConversationState.NEGOTIATING,
            ConversationState.COUNTER_OFFER,
            ConversationState.FINAL_OFFER,
        }
        if current_state in pickup_ready_states and has_enough_context:
            _money_words = ('sous', 'monnaie', 'argent', 'cash', 'billets')
            if (self._is_pickup_request(msg_lower) and
                    not any(mw in msg_lower for mw in _money_words)):
                return Intent(
                    event=ConversationEvent.CHOOSE_PICKUP,
                    confidence=0.95,
                    extracted_data={}
                )
            if self._is_location_request(msg_lower):
                return Intent(
                    event=ConversationEvent.ASK_LOCATION,
                    confidence=0.95,
                    extracted_data={}
                )
            delivery_result = self._check_delivery_request(msg_lower, context)
            if delivery_result:
                return delivery_result

        # 0b. Vérifier d'abord si c'est une objection ou frustration (priorité sur le prix)
        # Car "450K?? C'est cher!" n'est PAS une offre, c'est une objection
        has_objection_markers = any(m in msg_lower for m in [
            'cher', 'trop', 'beaucoup', '??', '?!', 'c\'est', 'quand même',
            'quand meme', 'vraiment', 'serieux', 'sérieux'
        ])

        # Contexte compétiteur : "j'ai vu à 24000 ailleurs" = objection, pas offre du client
        competitor_markers = [
            'ailleurs', 'concurrent', 'voisin', 'voisine',
            'on me propose', 'on m a propose', 'j ai vu', 'j ai eu une offre',
            'j ai une offre', 'quelqu un qui vend', 'quelqu un vend',
            'chez amazon', 'sur jumia', 'en ligne', 'en face',
            'le marchandeur', 'j ai mieux', 'j ai trouve moins',
        ]
        has_competitor_context = any(m in msg_lower for m in competitor_markers)

        # Si marqueurs d'objection OU contexte compétiteur + prix mentionné = c'est une objection
        price = self._extract_price(message)
        if price and (has_objection_markers or has_competitor_context):
            # C'est une objection sur le prix, pas une offre
            return Intent(
                event=ConversationEvent.OBJECTION_PRICE,
                confidence=0.85,
                extracted_data={"type": "price", "mentioned_price": price}
            )

        # 1. Extraction de prix comme offre réelle
        # L'offre doit être accompagnée de mots d'offre ou être seule
        if price:
            offer_markers = [
                'je fais', 'je propose', 'je donne', 'je mets', 'je paye',
                'je peux faire',  # δ07: "sans déconner je peux faire 15000"
                'mon offre', 'mon prix', 'maximum', 'dernier prix',
                'ok pour', 'd\'accord pour', 'ca te va', 'ça te va',
                'on dit', 'on fait', 'deal a', 'deal à'
            ]
            is_clear_offer = any(m in msg_lower for m in offer_markers)
            # Un prix seul (message court) est aussi considéré comme une offre
            is_short_price_message = len(message.strip()) < 30

            if is_clear_offer or is_short_price_message:
                return Intent(
                    event=ConversationEvent.PRICE_OFFER,
                    confidence=0.95,
                    extracted_data={"price": price}
                )

        # 1.5 Demande de localisation — AVANT visit_intent et acceptation
        # "Oui envoie", "envoie la position" contiennent "oui" qui matcherait l'acceptation
        # "je veux passer", "je viens demain" → implicitement besoin de la localisation
        # Note: localisation toujours détectable, même au 1er message
        if self._is_location_request(msg_lower):
            # 1.5b Vérifier si le client mentionne un MAUVAIS emplacement
            # Ex: "Vous êtes à Koumassi ?" alors que le magasin est à Bassam
            if merchant_data and '?' in message:
                correct_address = self._is_wrong_location_question(msg_lower, merchant_data)
                if correct_address:
                    return Intent(
                        event=ConversationEvent.ASK_LOCATION,
                        confidence=0.95,
                        extracted_data={"wrong_location": True, "correct_address": correct_address}
                    )
            return Intent(
                event=ConversationEvent.ASK_LOCATION,
                confidence=0.9,
                extracted_data={}
            )

        # 1.6 Intention de visite (APRÈS localisation, AVANT acceptation)
        # "je veux passer à la boutique" contient "je veux" qui serait détecté comme acceptation
        # Note: les messages avec localisation implicite ('je viens demain') sont déjà
        # capturés ci-dessus par _is_location_request
        is_early_stage = not has_enough_context or current_state == ConversationState.PRICE_PRESENTED
        if is_early_stage and self._is_visit_intent(msg_lower):
            return Intent(
                event=ConversationEvent.EXPRESS_INTEREST,
                confidence=0.85,
                extracted_data={"visit_intent": True}
            )

        # 2. Acceptation (pas au premier message — "je veux" n'est pas une acceptation)
        if self._is_acceptance(msg_lower) and has_enough_context:
            return Intent(
                event=ConversationEvent.ACCEPT_OFFER,
                confidence=0.9,
                extracted_data={}
            )

        # 3. Demande de livraison (avec contexte, pas au 1er message)
        if has_enough_context:
            delivery_result = self._check_delivery_request(msg_lower, context)
            if delivery_result:
                return delivery_result

        # 4. Demande de pickup/localisation (pas au 1er message)
        _money_words2 = ('sous', 'monnaie', 'argent', 'cash', 'billets')
        if (has_enough_context and self._is_pickup_request(msg_lower) and
                not any(mw in msg_lower for mw in _money_words2)):
            return Intent(
                event=ConversationEvent.CHOOSE_PICKUP,
                confidence=0.85,
                extracted_data={}
            )

        if self._is_location_request(msg_lower):
            return Intent(
                event=ConversationEvent.ASK_LOCATION,
                confidence=0.85,
                extracted_data={}
            )

        # 5. Fourniture d'adresse
        address = self._extract_address(message)
        if address:
            return Intent(
                event=ConversationEvent.PROVIDE_ADDRESS,
                confidence=0.8,
                extracted_data={"address": address}
            )

        # 6. Objections
        objection = self._detect_objection(msg_lower)
        if objection:
            return objection

        # 7. Frustration
        if self._is_frustrated(msg_lower, message):
            return Intent(
                event=ConversationEvent.EXPRESS_FRUSTRATION,
                confidence=0.85,
                extracted_data={}
            )

        # 8. Fin de conversation
        if self._is_goodbye(msg_lower):
            return Intent(
                event=ConversationEvent.SAY_GOODBYE,
                confidence=0.8,
                extracted_data={}
            )

        # 9. Question sur le prix
        if self._is_price_question(msg_lower):
            return Intent(
                event=ConversationEvent.PRICE_QUESTION,
                confidence=0.8,
                extracted_data={}
            )

        # 9.5 Question d'horaires (jamais inventés par le bot)
        if self._is_hours_question(msg_lower):
            return Intent(
                event=ConversationEvent.EXPRESS_INTEREST,
                confidence=0.8,
                extracted_data={"hours_question": True}
            )

        # 10. Expression d'intérêt (défaut si message court)
        if len(message) < 50 or self._shows_interest(msg_lower):
            return Intent(
                event=ConversationEvent.EXPRESS_INTEREST,
                confidence=0.6,
                extracted_data={}
            )

        # 10.5 BOOST SÉQUENCE: si le client répète un pattern → amplifier la confiance
        # Le bot analyse les 3-4 dernières intentions du client pour briser l'ambiguïté
        if intent_history and len(msg_lower.strip()) < 50:
            last = intent_history[-2:] if len(intent_history) >= 2 else intent_history

            # Pattern: client qui a enchaîné des objections de prix → prochain message négatif = au revoir
            if (last.count('OBJECTION_PRICE') >= 2 and
                    any(neg in msg_lower for neg in ['non', 'nan', 'pas', 'jamais', 'laisse', 'oublie', 'finalement'])):
                return Intent(
                    event=ConversationEvent.SAY_GOODBYE,
                    confidence=0.72,
                    extracted_data={"history_boosted": True}
                )

            # Pattern: client qui a fait 2+ offres consécutives → message avec prix = nouvelle offre (pas objection)
            if last.count('PRICE_OFFER') >= 2:
                boosted_price = self._extract_price(message)
                if boosted_price:
                    return Intent(
                        event=ConversationEvent.PRICE_OFFER,
                        confidence=0.92,
                        extracted_data={"price": boosted_price, "history_boosted": True}
                    )

            # Pattern: client qui a accepté puis pose une question → rester en accord, pas re-négociation
            if 'ACCEPT_OFFER' in last and current_state == ConversationState.DEAL_AGREED:
                return Intent(
                    event=ConversationEvent.EXPRESS_INTEREST,
                    confidence=0.75,
                    extracted_data={"post_deal_followup": True}
                )

        # Défaut: premier message ou intérêt général
        return Intent(
            event=ConversationEvent.FIRST_MESSAGE,
            confidence=0.5,
            extracted_data={}
        )

    def _resolve_with_bot_context(self, msg_lower: str, last_bot_message: str) -> Optional[Intent]:
        """
        Résout les intentions ambiguës grâce au contexte du dernier message du bot.

        Exemples concrets:
        - Bot: "Je te propose 16 000 F, ça te va ?" → Client: "ok" → ACCEPT_OFFER
        - Bot: "Livraison ou pickup ?" → Client: "pickup" / "je passe" → CHOOSE_PICKUP
        - Bot: "Ton adresse ?" → Client: "Cocody Angré" → PROVIDE_ADDRESS
        """
        bot_lower = last_bot_message.lower()
        msg_stripped = msg_lower.strip().rstrip('?.! ')

        # Petits mots de confirmation (positifs courts)
        short_confirmations = {
            'ok', 'bon', 'bien', 'd accord', 'daccord', 'ça marche', 'ca marche',
            'ok ok', 'oui', 'ouais', 'weh', 'yep', 'parfait', 'super', 'top',
            'yes', 'marche', 'cool', 'nickel', 'ça le fait', 'ca le fait',
            'deal', 'accord', 'dja', 'on dit quoi', 'on dit',
        }
        negative_words = {'non', 'nan', 'nah', 'trop', 'cher', 'pas', 'jamais', 'impossible'}
        is_short_positive = (
            msg_stripped in short_confirmations or
            len(msg_lower.strip()) <= 12
        ) and not any(neg in msg_lower for neg in negative_words)

        # --- Pattern 1: Bot vient de faire une contre-offre → court oui = ACCEPT_OFFER ---
        counter_offer_signals = [
            'je te propose', 'pour toi je fais', 'je peux faire', 'je descends à',
            'je baisse à', 'je t\'offre', 'dernier prix', 'prix spécial', 'prix special',
            'pour toi,', 'pour toi.', 'tu veux bien', 'ça te va', 'ca te va',
            'je te fais', 'je vous propose', 'on peut faire',
        ]
        if is_short_positive and any(sig in bot_lower for sig in counter_offer_signals):
            return Intent(
                event=ConversationEvent.ACCEPT_OFFER,
                confidence=0.82,
                extracted_data={"context_resolved": True, "ctx": "after_counter_offer"}
            )

        # --- Pattern 1.5: Bot a posé une question d'information (pas une contre-offre) ---
        # "Tu veux plus de détails ?" + "oui oui" → EXPRESS_INTEREST (info demandée, pas accord d'achat)
        # CRITIQUE: sans ça, "oui" après une question info = faux deal déclaré
        info_question_signals = [
            'plus de details', 'plus d info', 'plus d infos', 'plus d information',
            'tu veux savoir', 'je t explique', 'tu veux que j', "t'en dire plus",
            'te dire plus', 'te donner plus', 'te montrer', 'voir des photos',
            'tu veux voir', 'je peux t expliquer', 'je peux expliquer',
            'tu veux des photos', 'tu veux la description',
        ]
        if is_short_positive and any(sig in bot_lower for sig in info_question_signals):
            return Intent(
                event=ConversationEvent.EXPRESS_INTEREST,
                confidence=0.80,
                extracted_data={"context_resolved": True, "ctx": "after_info_question"}
            )

        # --- Pattern 2: Bot a demandé le choix livraison/pickup ---
        # IMPORTANT: exclure les questions ("vous livrez?") — c'est une question, pas un choix
        delivery_choice_signals = [
            'livraison ou', 'pickup ou livraison', 'livrer ou', 'récupérer ou',
            'recuperer ou', 'je te livre ou', 'tu préfères', 'tu preferes',
            'livraison ou pickup', 'pickup ou',
        ]
        is_question = '?' in msg_lower
        if not is_question and any(sig in bot_lower for sig in delivery_choice_signals):
            pickup_words = [
                'pickup', 'je passe', 'je viens', 'je recupere', 'je récupère',
                'retrait', 'boutique', 'magasin', 'recuperer', 'récupérer', 'je passe chercher',
            ]
            delivery_words = [
                'livraison', 'livre moi', 'livre-moi', 'chez moi',
                'à domicile', 'a domicile',
            ]
            if any(pw in msg_lower for pw in pickup_words):
                return Intent(
                    event=ConversationEvent.CHOOSE_PICKUP,
                    confidence=0.88,
                    extracted_data={"context_resolved": True, "ctx": "after_delivery_question"}
                )
            if any(dw in msg_lower for dw in delivery_words):
                return Intent(
                    event=ConversationEvent.CHOOSE_DELIVERY,
                    confidence=0.88,
                    extracted_data={"context_resolved": True, "ctx": "after_delivery_question"}
                )

        # --- Pattern 3: Bot a demandé l'adresse de livraison ---
        address_request_signals = [
            'ton adresse', 'votre adresse', 'tu habites', 'tu es situé',
            'tu te trouves', 'tu livres où', 'adresse de livraison', 'livraison c est où',
            'quartier', 'zone de livraison',
        ]
        if any(sig in bot_lower for sig in address_request_signals):
            quartiers = [
                'cocody', 'yopougon', 'abobo', 'adjamé', 'adjame', 'plateau',
                'koumassi', 'marcory', 'treichville', 'attécoubé', 'attecoube',
                'port bouet', 'bassam', 'bingerville', 'angré', 'angre',
                'riviera', 'deux plateaux', '2 plateaux', 'williamsville',
            ]
            if any(q in msg_lower for q in quartiers):
                return Intent(
                    event=ConversationEvent.PROVIDE_ADDRESS,
                    confidence=0.88,
                    extracted_data={"context_resolved": True, "ctx": "after_address_request"}
                )

        return None

    def _normalize_message(self, msg: str) -> str:
        """
        Normalise le message pour mieux comprendre:
        - Fautes de frappe courantes
        - Abréviations WhatsApp
        - Expressions nouchi/ivoiriennes
        - Raccourcis numériques
        """
        # PRIORITÉ 0: Normaliser apostrophes et accents EN PREMIER
        # pour que le nouchi_map et les patterns matchent les formes ASCII
        # Ex: 'solder ça' → 'solder ca' → matche 'solder ca' dans nouchi_map
        msg = msg.replace('\u2019', ' ').replace('\u2018', ' ').replace("'", ' ')
        try:
            msg_nfd = unicodedata.normalize('NFD', msg)
            msg = ''.join(c for c in msg_nfd if unicodedata.category(c) != 'Mn')
        except Exception:
            pass

        # Abréviations WhatsApp → forme complète
        abbreviations = {
            'svp': 's il vous plait',
            'stp': 's il te plait',
            'pk': 'pourquoi',
            'pr': 'pour',
            'bcp': 'beaucoup',
            'tjrs': 'toujours',
            'tt': 'tout',
            'mnt': 'maintenant',
            'mtn': 'maintenant',
            'pcq': 'parce que',
            'jsp': 'je sais pas',
            'jpp': 'j en peux plus',
            'lol': '',
            'bjr': 'bonjour',
            'bsr': 'bonsoir',
            'slt': 'salut',
            'nn': 'non',
            'mm': 'meme',
            'ac': 'avec',
            'ss': 'sans',
            'pb': 'probleme',
            'rdv': 'rendez vous',
            'cmt': 'comment',
            'koi': 'quoi',
            'kan': 'quand',
            'ki': 'qui',
            'ya': 'il y a',
            # Abréviations africaines fréquentes
            'dispo': 'disponible',
            'livr': 'livraison',
            'qd': 'quand',
            'dc': 'donc',
            'pq': 'pourquoi',
            'biz': 'bisous',
            'wsh': 'bonjour',       # verlan familier
            'frr': 'frere',
            'frero': 'frere',
            'gros': 'ami',
            'chef': 'vendeur',      # "chef c est combien" = ivoirien/sénégalais
            'patron': 'vendeur',
            'boss': 'vendeur',
        }
        for abbr, full in abbreviations.items():
            msg = re.sub(r'\b' + abbr + r'\b', full, msg)

        # Expressions nouchi/ivoiriennes → intention équivalente
        nouchi_map = {
            # ── Expressions complexes AVANT les mots simples (ordre critique) ──
            'wari yeke obe': 'combien',  # dioula: "combien ça coûte" (AVANT 'wari')
            'combien c est': 'combien',
            'c est combien du coup': 'combien',
            'ca fait combien': 'combien',
            'ca coute combien': 'combien',

            # ── Acceptation / achat ──
            'wari': 'argent',
            'dja': 'accord',
            'djaa': 'accord',
            'on se comprend': 'accord',
            'on dit quoi': 'accord',
            'c est dit': 'accord',          # CI: "c'est dit" = deal (sans apostrophe)
            'c est regle': 'accord',        # CI: "c'est réglé" = deal
            'c est plie': 'accord',         # CI: "c'est plié" = deal
            'c est scelle': 'accord',       # CI: "c'est scellé" = deal
            'on est bon': 'accord',         # CI: on s'est mis d'accord
            'on est d accord': 'accord',    # CI: idem
            'ca tombe': 'accord',           # CI: ça tombe = deal
            'ca chute': 'accord',           # CI: ça chute = deal
            'je ramasse': 'je le prends',   # CI: je ramasse = je prends
            'ca passe': 'accord',           # CI: ça passe = deal
            'ca coule': 'accord',           # CI: ça coule = deal
            'na djeu': 'accord',            # CI: na djeu = deal
            'on se met': 'accord',          # CI: on se met d'accord
            'ca coupe': 'accord',           # CI: ça coupe = deal
            'solder ca': 'je le prends',    # CI: solder ça = acheter
            'deal on dit': 'accord',
            'on fait comment': 'comment on fait',
            'c est comment': 'c est combien',
            'c\'est comment': 'c est combien',
            'c comment': 'c est combien',
            'hein': '',                      # particule vide
            'oo': 'oui',
            'weh': 'oui',                   # AVANT 'we'
            'wê': 'oui',
            'we': 'oui',
            'ehen': 'oui',                  # CI/béninois: oui marqué
            'eeh': 'oui',
            'nan': 'non',
            'nah': 'non',
            'nope': 'non',
            'laisses tomber': 'annuler',
            'laisse tomber': 'annuler',
            'laisse': 'annuler',
            'j abandonne': 'annuler',
            'oublie': 'annuler',            # "oublie ça" = annuler
            'oublie ca': 'annuler',

            # ── Prix / négociation ──
            'je cherche pas': 'c est trop cher',
            'c est cho': 'c est cher',
            'c\'est cho': 'c est cher',
            'c cho': 'c est cher',
            'cho': 'cher',
            'c est pas possible': 'c est trop cher',
            'trop fort': 'trop cher',
            'fort trop': 'trop cher',
            'gonfle': 'cher',
            'gonflé': 'cher',
            'salé': 'cher',                 # "c'est salé" = c'est cher
            'sale': 'cher',
            'exagere': 'trop cher',
            'exagéré': 'trop cher',
            'djara': 'prix',                # dioula: "prix" → aide extract_price
            'ka doni': 'combien',           # bambara: "combien ça coûte"

            # ── Localisation ──
            # Note: 'c est ou', 'vous etes ou' RETIRÉS du nouchi_map car ils matchent
            # en sous-chaîne 'c est ouvert', 'vous etes ouverts' → faux positifs localisation
            # Ces patterns sont désormais gérés par regex word-boundary dans _is_location_request
            'vous etes a': 'vous êtes à',
            'vous situez': 'vous êtes situé',
            'votre plan': 'votre adresse',  # "envoie ton plan" = envoie la localisation
            'envoie le plan': 'envoie la localisation',
            'envoie ton plan': 'envoie la localisation',
            'la position': 'la localisation',

            # ── Désignation d'un produit ──
            'lui la': 'je veux celui-la',
            'lui là': 'je veux celui-la',
            'elle la': 'je veux celle-la',
            'elle là': 'je veux celle-la',
            'celui la': 'je veux celui-la',
            'celle la': 'je veux celle-la',
            'le truc la': 'l article',
            'le machin la': 'l article',

            # ── Qualité / confiance ──
            'c est quoi comme qualite': 'quelle est la qualite',
            'c est original': 'c est authentique',
            'c est fake': 'c est faux',
            'c est genuine': 'c est authentique',

            # ── Divers particules / réactions ──
            'au revoir hein': 'au revoir',
            'merci hein': 'merci',
            'je kiffe': 'j aime',
            'kiffe': 'aime',
            'waw': 'super',
            'waow': 'super',
            'OMG': 'super',
            'lol': '',
            'mdr': '',
            'xd': '',
            'ahah': '',
            'haha': '',
        }
        for nouchi, french in nouchi_map.items():
            if nouchi in msg:
                msg = msg.replace(nouchi, french)

        # Fautes de frappe courantes
        typos = {
            'combient': 'combien',
            'dispobible': 'disponible',
            'disponnible': 'disponible',
            'dispoble': 'disponible',
            'disponble': 'disponible',
            'lvirasion': 'livraison',
            'livrason': 'livraison',
            'boutque': 'boutique',
            'boutiqe': 'boutique',
            'magsin': 'magasin',
            'magasen': 'magasin',
            'adrese': 'adresse',
            'adrsse': 'adresse',
            'qualitee': 'qualite',
            'qualité': 'qualite',
            'j\'veux': 'je veux',
            'j\'prends': 'je prends',
            'j\'peux': 'je peux',
            'j\'ai': 'j ai',
        }
        for typo, correct in typos.items():
            msg = msg.replace(typo, correct)

        return msg

    def _extract_price(self, message: str) -> Optional[float]:
        """Extrait un prix du message"""
        msg = message.lower()

        # Pattern "450k" ou "450K"
        k_match = re.search(r'(\d+)\s*k\b', msg)
        if k_match:
            return float(k_match.group(1)) * 1000

        # Pattern "450 000" avec espaces
        space_match = re.search(r'(\d{1,3}(?:\s\d{3})+)', msg)
        if space_match:
            return float(space_match.group(1).replace(' ', ''))

        # Pattern "450000" simple (4+ chiffres)
        simple_match = re.search(r'\b(\d{4,})\b', msg)
        if simple_match:
            return float(simple_match.group(1))

        return None

    def _is_acceptance(self, msg: str) -> bool:
        """Détecte si le client accepte — français + nouchi + abréviations"""
        exact_accepts = [
            # Français standard
            'ok', 'oui', 'deal', 'vendu', 'marche', 'adjuge',
            'd accord', 'daccord', 'je le prends', 'je la prends', 'je les prends',
            # Note: 'je prends' et 'je veux' seuls → for-phrase loop (avec exclusions)
            'ca marche', 'c est bon', 'parfait', 'top', 'impec',
            'on fait comme ca', 'je suis d accord', 'je valide',
            'je le veux', 'je la veux', 'c est deal',
            'je suis partant', 'je suis partante', 'banco',
            # Accord après négociation
            'c est pris', 'va pour ca', 'ca ira', 'on y va', 'allez',
            'ca roule', 'c est valide', 'c est ok', 'c est pour moi', 'regle',
            'ca me va', 'ca me convient', 'me convient',
            # Nouchi / ivoirien courant
            'dja', 'djaa', 'on se comprend', 'on dit quoi', 'accord',
            'we', 'oo',
            # Nouchi / ivoirien avancé
            'na djeu', 'on se met', 'ca coupe', 'finit', 'c bon', 'c clair',
            'on est bon', 'ca tombe', 'ca chute', 'je ramasse', 'ca passe', 'ca coule',
            'c est plie', 'c est scelle', 'c est regle',
            'on est d accord', 'c est dit',
            # Anglais / franglais courant
            'yes', 'yep', 'yop', 'agreed', 'done', 'let s go', 'go',
            'let s do it', 'i ll take it', 'sold', 'confirmed',
            # Paiement imminent (accord implicite)
            'je viens avec les sous', 'je viens avec la monnaie', 'je viens avec l argent',
            'je ramene les sous', 'j amene les sous', 'avec les sous', 'avec la monnaie',
            # Décisions finales / commandes explicites
            'c est fait', 'j achete', 'je veux acheter', 'je veux commander',
            'j ai decide de prendre', 'j ai pris ma decision',
            'je passe commande', 'je fais l achat', 'ma commande',
        ]

        # Phrases annulant l'accord ("ok mais trop cher" ≠ accord, "deal si tu baisses" ≠ accord)
        retraction_phrases = [
            'mais non', 'trop cher', 'j ai change d avis', 'change d avis',
            'pour une autre fois', 'si tu baisses', 'si la qualite',
            'mais quand meme', 'pas sur',
            # Annulations explicites
            'annuler', 'bye', 'j abandonne',
            # Négation explicite dans le message (ex: "deal deal deal (non)")
            '(non)',
            # Abandon vers la concurrence ("c'est bon j'ai trouvé ailleurs")
            'trouve ailleurs', 'j ai trouve ailleurs', 'j ai trouve mieux',
            'achete ailleurs', 'commande ailleurs', 'moins cher ailleurs',
        ]

        msg_stripped = msg.strip()
        # Supprimer ponctuation terminale: "go!" → "go", "banco!" → "banco"
        msg_stripped_clean = msg_stripped.rstrip('!?.,:;…')

        # Message court d'acceptation exacte (jamais si c'est une question)
        if msg_stripped_clean in exact_accepts and '?' not in msg_stripped:
            return True

        # "pas sur" n'est pas une rétractation si un prix est présent dans le message
        # Ex: "ok 14000 mais je suis pas encore 100%" → prix auto-accepté, hésitation ignorée
        has_price_in_msg = bool(self._extract_price(msg))
        effective_retractions = retraction_phrases if not has_price_in_msg else [
            r for r in retraction_phrases if r != 'pas sur'
        ]

        # Indicateur: le message est une question (ex: "ok c'est combien?" ≠ accord)
        is_question_msg = '?' in msg_stripped

        # Mots indiquant une hésitation ou un compliment (non-achat) après un mot d'acceptation
        hesitation_starters = (
            'mais', 'merci', 'vois', 'je vois', 'je verrai', 'voir', 'reflechir',
            'vais reflechir', 'et si', 'si jamais', 'je pense', 'je vais voir',
            # Délais et report
            'a demain', 'plus tard', 'bonne journee', 'on verra', 'j attends',
            'reviens', 'je reviens', 'ok ok',
            # Effort / négociation (pour "allez fais un geste")
            'geste', 'effort', 'un geste', 'petit effort',
        )
        # Noms qui transforment "top/parfait" en compliment (pas achat)
        compliment_nouns = ('produit', 'article', 'truc', 'comme', 'qualite', 'affaire', 'machin')

        # Phrases d'acceptation au début du message
        for accept in exact_accepts:
            if msg_stripped_clean.startswith(accept + ' ') or msg_stripped_clean.startswith(accept + ','):
                # "ok mais c'est cher?" n'est pas une acceptation
                if is_question_msg:
                    continue
                # Vérifier si suivi d'une hésitation ("ok je vois", "ok merci", "ok je vais réfléchir")
                rest = msg_stripped_clean[len(accept):].strip().lstrip(',').strip()
                if any(rest == hw or hw in rest for hw in hesitation_starters):
                    continue
                # "top produit", "parfait comme produit" → compliment, pas achat
                if accept in ('top', 'parfait', 'super', 'excellent') and rest:
                    if any(cn in rest for cn in compliment_nouns):
                        continue
                # Négation directe après le mot d'acceptation ("j'achète pas ça", "ok plus")
                if rest and rest.split()[0] in ('pas', 'plus', 'jamais', 'non', 'no', 'nah', 'nan', 'nope'):
                    continue
                # Vérifier l'absence de rétractation ("ok mais trop cher" ≠ accord)
                if not any(r in msg_stripped_clean for r in effective_retractions):
                    return True

        # Phrases d'acceptation à la FIN du message (accord tardif)
        # Ex: "non c'est bon je le prends", "pas de problème banco"
        _negations = ('pas', 'non', 'jamais', 'plus', 'nah', 'nan', 'nope', 'no')
        for accept in exact_accepts:
            if msg_stripped_clean.endswith(' ' + accept):
                # "c'est quoi ce deal?" n'est pas une acceptation
                if is_question_msg:
                    continue
                # Vérifier qu'il n'y a pas de négation directe avant le mot d'acceptation
                prefix = msg_stripped_clean[:-(len(accept) + 1)].strip()
                if any(prefix == neg or prefix.endswith(' ' + neg) for neg in _negations):
                    continue
                # Répétition du même mot = hésitation ("ok ok ok", "deal deal deal")
                if prefix.endswith(' ' + accept) or prefix == accept:
                    continue
                if not any(r in msg_stripped_clean for r in effective_retractions):
                    return True

        # "je prends" ou "je veux" sans négation ni exclusion
        # Note: 'plus' est une négation implicite ("je veux plus ça" = "je ne veux plus ça")
        for phrase in ['je prends', 'je veux']:
            if phrase in msg and 'pas' not in msg and 'ne ' not in msg and 'plus' not in msg:
                exclusions = ['soin', 'note', 'noter', 'en compte', 'le temps', 'savoir',
                              'dire', 'passer', 'voir', 'connaitre', 'regarder', 'visiter',
                              # Quantités → négociation sur le nombre, pas encore accord
                              'paquets', 'paquet', 'kilo', 'kg', 'piece', 'pieces', 'unites',
                              'carton', 'cartons', 'douzaine', 'dizaine']
                if not any(excl in msg for excl in exclusions):
                    return True

        # "c'est good/cool/parfait" → acceptation
        if any(p in msg for p in ['c est good', 'c est cool', 'c est top', 'impeccable', 'nickel', 'impec']):
            return True

        return False

    def _check_delivery_request(self, msg: str, context: ConversationMemory) -> Optional[Intent]:
        """
        Détecte une demande de livraison EN CONTEXTE.
        Évite les faux positifs (plaintes, questions sur le prix de livraison).
        """
        # Contextes négatifs - ce n'est PAS une demande
        negative_contexts = [
            'pas de livraison', 'sans livraison', 'livraison?', 'livraison ?',
            'combien la livraison', 'prix de la livraison', 'frais de livraison',
            'coût de livraison', 'cout de livraison', 'cher', 'trop',
            'voleur', 'arnaque', 'abuse', 'abusé', 'exagère'
        ]

        if any(neg in msg for neg in negative_contexts):
            return None

        # Question sur la livraison (pas une demande)
        if '?' in msg and 'livr' in msg:
            return None

        # Demandes affirmatives
        # Note: svp/stp normalisés en "s il vous/te plait" → inclure les deux formes
        delivery_requests = [
            'je veux la livraison',
            'livraison svp', 'livraison stp',
            'livraison s il vous plait', 'livraison s il te plait',
            'livre-moi', 'livrez-moi', 'livrer chez moi', 'livraison chez moi',
            'je préfère la livraison', 'je prefere la livraison',
            'oui livraison', 'ok livraison', 'avec livraison',
            'fais-moi livrer', 'fais moi livrer', 'pour la livraison'
        ]

        if any(req in msg for req in delivery_requests):
            return Intent(
                event=ConversationEvent.CHOOSE_DELIVERY,
                confidence=0.9,
                extracted_data={}
            )

        return None

    def _is_pickup_request(self, msg: str) -> bool:
        """Détecte une demande de pickup — français + nouchi"""
        pickup_keywords = [
            # Français standard
            'je viens', 'je passe', 'passer chercher', 'viens chercher',
            'recuperer', 'sur place', 'en personne',
            'moi meme', 'je me deplace', 'je viens chercher',
            'je viendrai', 'je passerai', 'je vais passer',
            'retrait', 'enlever moi meme', 'venir chercher',
            # Nouchi / ivoirien
            'je viens ramasser', 'je viens prendre', 'je passe prendre',
            'je viens voir', 'on se voit', 'on se retrouve',
            # Expressions courantes
            'je me deplace', 'je viens a la boutique', 'je viens au magasin',
            'je vais venir', 'je compte venir', 'je peux venir',
        ]
        # Exclure toutes les questions (pickup = engagement, pas question)
        if '?' in msg:
            return False
        # Exclure les messages avec argent → c'est une acceptation de paiement, pas juste pickup
        if any(mw in msg for mw in ['sous', 'monnaie', 'argent', 'cash', 'billets']):
            return False
        # Exclure "je vais passer commande" (= passer une commande ≠ venir chercher)
        if 'commande' in msg:
            return False
        return any(kw in msg for kw in pickup_keywords)

    def _is_location_request(self, msg: str) -> bool:
        """Détecte une demande de localisation du magasin — français + nouchi + anglais"""
        # EXCLUSION PRIORITAIRE: Questions d'horaires (avant toute autre vérification)
        # "c'est ouvert maintenant?", "la boutique ouvre quand?" ≠ demande de localisation
        hours_markers = ('ouvert', 'ouvre', 'ferme', 'horaire', 'ouverts', 'ouverte',
                         'ouverture', 'fermeture')
        if '?' in msg and any(h in msg for h in hours_markers):
            return False

        # Phrases explicites de demande d'adresse
        explicit_location = [
            # Français (accent-normalisé par le normalizer)
            # Note: 'c est ou', 'vous etes ou', 'tu es ou' → vérification word-boundary ci-dessous
            'ou se trouve', 'ou est le magasin', 'ou est la boutique',
            'adresse du magasin', 'localisation', 'position du magasin',
            'position de la boutique', 'envoie la position',
            'envoie moi la position', 'la position', 'avoir la position',
            'ou je peux venir', 'je viens ou', 'comment venir', 'comment je viens',
            'comment on peut venir', 'comment on vient',
            'situe ou', 'situer',
            # Visites implicites → besoin de l'adresse
            'je veux passer', 'je veux venir',
            'je viens demain', 'je passerai demain', 'je viendrai demain',
            'je passe demain', 'je viens ce soir', 'je viens ce matin',
            'je passerai vous voir', 'je viens vous voir', 'je passe vous voir',
            'je veux passer prendre', 'je passerai prendre', 'je viendrai prendre',
            # Demandes d'adresse directe
            'l adresse', 'quelle adresse', 'adresse stp', 'adresse svp',
            'adresse s il vous plait', 'adresse s il te plait',
            'c est quoi l adresse', 'donnez moi l adresse', 'donne moi l adresse',
            'envoie moi l adresse', 'envoie l adresse', 'envoyez l adresse',
            'pin de localisation', 'partagez la localisation', 'partager la localisation',
            # Demandes d'envoi
            'envoie', 'envoi', 'oui envoie', 'oui envoi',
            'envoie moi', 'envoi moi', 'oui la position',
            'donne moi la position', 'donne la position',
            'partage la position', 'partage ton adresse',
            # Nouchi / ivoirien + questions sur la venue au magasin
            'c est comment pour venir', 'comment je fais pour venir',
            'vous etes situe ou', 'ou vous etes', 'dans quel coin',
            'on peut venir comment', 'votre adresse', 'ton adresse',
            'quel secteur', 'c est quel zone', 'quel zone', 'quel quartier',
            'quel endroit', 'a quel endroit', 'dans quel endroit',
            'je peux venir', 'on peut venir',
            'le local c est ou', 'ton local c est ou', 'le shop c est ou',
            'vous garez ou', 'votre coin c est ou', 'le coin c est ou',
            'chez vous c est ou', 'dans quel bled', 'tu fais ton business',
            'ton business ou', 'tu es au marche',
            # Anglais
            'where are you', 'what s your address', 'where is your shop',
            'where is your store', 'how do i get there', 'how can i come',
            'i want to come', 'i ll come pick', 'send me your location',
            'share your location', 'the address please', 'where are you located',
            'what s the location', 'i want to pick up', 'i ll come by',
            'your address', 'where do you', 'how to get to',
        ]

        if any(loc in msg for loc in explicit_location):
            # Exclure les adresses non-physiques (mail, facturation, commerciale...)
            non_physical_ctx = (
                'mail', 'email', 'commerciale', 'facturation', 'fabricant',
                'sur la boite', 'noter', 'pour apres', 'interesse pas',
                'm interesse pas', 'pas l adresse', 'pas maintenant',
                'votre site', 'un site', 'whatsapp', 'livraison ca',
            )
            if any(np in msg for np in non_physical_ctx):
                return False
            return True

        # Vérification word-boundary pour les patterns courts susceptibles de faux positifs
        # "c est ou" ne doit PAS matcher "c est ouvert" (où 'ou' est préfixe de 'ouvert')
        if (re.search(r'\bc est ou\b', msg) or
                re.search(r'\bvous etes ou\b', msg) or
                re.search(r'\btu es ou\b', msg)):
            return True

        # "magasin" ou "boutique" + question ou demande de lieu
        # Note: 'ou' doit être un mot isolé (éviter "boutique" qui contient "ou")
        location_words = ['magasin', 'boutique', 'shop', 'chez vous', 'local', 'bled', 'business']
        direction_words_exact = ['?', 'comment', 'adresse', 'situe', 'localise', 'trouve',
                                  'aller', 'venir', 'endroit']
        has_location_word = any(lw in msg for lw in location_words)
        has_direction = (any(dw in msg for dw in direction_words_exact) or
                         bool(re.search(r'\bou\b', msg)))  # 'ou' isolé, pas substr de boutique
        if has_location_word and has_direction:
            # Exclure questions d'existence pure ("tu as une boutique?" ≠ "où est ta boutique?")
            existence_questions = [
                'tu as une boutique', 'vous avez une boutique',
                'il y a une boutique', 'tu as un magasin', 'vous avez un magasin',
            ]
            is_existence_question = any(eq in msg for eq in existence_questions)
            # Exclure questions d'horaires même avec location_words
            is_hours_with_location = ('?' in msg and
                                      any(h in msg for h in hours_markers))
            if not is_existence_question and not is_hours_with_location:
                return True
            # Si c'est une question d'existence → tomber sur le check quartier

        # Question avec un nom de quartier/ville = demande de confirmation de localisation
        quartiers = [
            'abobo', 'yopougon', 'cocody', 'plateau', 'adjame',
            'marcory', 'treichville', 'koumassi', 'port-bouet', 'port bouet',
            'bingerville', 'anyama', 'angre', 'riviera',
            'williamsville', 'attoban', 'palmeraie', 'bassam', 'grand-bassam',
            'mocville', 'mokcville', 'zone 4', 'vallon', '2 plateaux',
        ]
        # γ03: "vous livrez à Cocody?" = zone de livraison, PAS localisation du magasin
        delivery_zone_indicators = ['livrez', 'livraison', 'livrer', 'livrable']
        if '?' in msg and any(q in msg for q in quartiers):
            if not any(dk in msg for dk in delivery_zone_indicators):
                return True

        return False

    def _extract_address(self, message: str) -> Optional[str]:
        """Extrait une adresse du message"""
        msg_lower = message.lower()

        # Si c'est une question → ce n'est PAS une adresse fournie
        # Ex: "Vous a koumassi ?" = question, pas une adresse
        if '?' in message:
            return None

        # Quartiers d'Abidjan
        quartiers = [
            'abobo', 'yopougon', 'cocody', 'plateau', 'adjamé', 'adjame',
            'marcory', 'treichville', 'koumassi', 'port-bouet', 'port bouet',
            'bingerville', 'anyama', 'angré', 'angre', 'riviera', '2 plateaux',
            'deux plateaux', 'williamsville', 'attoban', 'palmeraie'
        ]

        # Vérifier si un quartier est mentionné
        for quartier in quartiers:
            if quartier in msg_lower:
                return message.strip()

        # Vérifier si un numéro de téléphone est présent (signe d'adresse)
        if re.search(r'\d{8,}', message):
            return message.strip()

        # Mots-clés d'adresse
        address_keywords = ['rue', 'avenue', 'boulevard', 'quartier', 'commune', 'près de', 'à côté']
        if any(kw in msg_lower for kw in address_keywords):
            return message.strip()

        return None

    def _detect_objection(self, msg: str) -> Optional[Intent]:
        """Détecte le type d'objection"""
        # Prix
        price_objections = [
            'trop cher', 'cher', 'budget', 'pas les moyens',
            'moins cher ailleurs', 'ailleurs moins cher', 'concurrent',
            'soi disant',   # δ03: "soi-disant 18500?" → ironie sur le prix
            'raisonnable',  # δ06: "tu crois c'est raisonnable?" → question rhétorique
            'c est fort',   # ζ07: "c'est fort ce prix" → nouchi = c'est cher
        ]
        if any(obj in msg for obj in price_objections):
            return Intent(
                event=ConversationEvent.OBJECTION_PRICE,
                confidence=0.85,
                extracted_data={"type": "price"}
            )

        # Qualité
        quality_objections = [
            'original', 'authentique', 'vrai', 'faux', 'copie',
            'contrefaçon', 'qualité', 'qualite'
        ]
        if any(obj in msg for obj in quality_objections) and '?' in msg:
            return Intent(
                event=ConversationEvent.OBJECTION_QUALITY,
                confidence=0.8,
                extracted_data={"type": "quality"}
            )

        # Confiance
        # Note: 'sur' retiré car trop large ("plus sur la qualité" → faux positif)
        trust_objections = [
            'confiance', 'arnaque', 'peur', 'méfiant', 'sûr', 'pas sûr', 'doute'
        ]
        # "arnaqueur", "escroc" = accusation directe = frustration, pas objection
        trust_exclusions = ['arnaqueur', 'escroque', 'escroc']
        if any(obj in msg for obj in trust_objections) and not any(excl in msg for excl in trust_exclusions):
            return Intent(
                event=ConversationEvent.OBJECTION_TRUST,
                confidence=0.8,
                extracted_data={"type": "trust"}
            )

        # Timing
        timing_objections = [
            'réfléchir', 'reflechir', 'plus tard', 'pas maintenant',
            'demain', 'la semaine prochaine', 'rappeler'
        ]
        if any(obj in msg for obj in timing_objections):
            return Intent(
                event=ConversationEvent.OBJECTION_TIMING,
                confidence=0.8,
                extracted_data={"type": "timing"}
            )

        return None

    def _is_frustrated(self, msg: str, original: str) -> bool:
        """Détecte la frustration"""
        frustration_words = [
            'voleur', 'arnaque', 'arnaqueur', 'escroc', 'escroque', 'menteur', 'idiot',
            'fou', 'folle', 'dingue', 'merde', 'putain',
            'tu abuses', 'tu exagères', 'n\'importe quoi', 'c\'est du vol'
        ]

        if any(fw in msg for fw in frustration_words):
            return True

        # Majuscules excessives
        if len(original) > 10:
            uppercase_count = sum(1 for c in original if c.isupper())
            if uppercase_count > len(original) * 0.5:
                return True

        # Ponctuation excessive
        if original.count('!') >= 3 or original.count('?') >= 3:
            return True

        return False

    def _is_goodbye(self, msg: str) -> bool:
        """Détecte une fin de conversation — français + nouchi"""
        goodbyes = [
            # Français
            'bye', 'au revoir', 'ciao', 'non merci', 'pas interesse',
            'laisse tomber', 'laisse', 'c est bon laisse',
            'bonne continuation', 'bonne journee', 'a une autre fois',
            'c est pas pour moi', 'ca m interesse pas',
            # Nouchi / ivoirien
            'annuler', 'j abandonne', 'partez',
            'on oublie', 'oublie', 'c est bon oublie',
            'j ai change d avis', 'finalement non',
            'ca degage', 'je degage',   # ζ03: "ça dégage ici" = je pars = SAY_GOODBYE
            # Anglais courant
            'forget it', 'never mind', 'not interested', 'no thanks',
        ]

        if len(msg) < 50:
            return msg.strip() in goodbyes or any(g in msg for g in goodbyes)

        return False

    def _is_price_question(self, msg: str) -> bool:
        """Détecte une question sur le prix — français + nouchi"""
        price_questions = [
            # Français
            'combien', 'prix', 'coute', 'a combien', 'le tarif',
            'ca fait combien', 'c est a combien', 'vous vendez a combien',
            'c est quoi le prix', 'quel est le prix', 'le cout',
            # Nouchi / ivoirien
            'c est comment', 'c comment', 'c est quoi comme prix',
            'vous avez le prix', 'wari yeke obe',  # dioula: combien ça coûte
            # Abréviations
            'le px', 'le $', 'le pr',
        ]
        return any(pq in msg for pq in price_questions)

    def _is_visit_intent(self, msg: str) -> bool:
        """Détecte une intention de visite au premier message"""
        visit_keywords = [
            'passer voir', 'passe voir', 'venir voir', 'viens voir',
            'passer a la boutique', 'passer à la boutique',
            'venir a la boutique', 'venir à la boutique',
            'visiter la boutique', 'visiter le magasin',
            'je passe', 'je viens', 'passer au magasin',
            'voir a la boutique', 'voir à la boutique',
            'voir au magasin'
        ]
        if any(kw in msg for kw in visit_keywords):
            # "je viens avec les sous" = paiement = accord, pas visite
            if any(mw in msg for mw in ('sous', 'monnaie', 'argent', 'cash')):
                return False
            # "je passe commande" = commander = accord, pas visite au magasin
            if 'commande' in msg:
                return False
            return True
        return False

    def _is_wrong_location_question(self, msg: str, merchant_data: Dict) -> Optional[str]:
        """
        Détecte si le client mentionne un mauvais emplacement.
        Retourne l'adresse correcte du marchand si le client se trompe, None sinon.
        """
        if not merchant_data or not merchant_data.get('address'):
            return None

        merchant_address = merchant_data['address'].lower()

        # Liste des quartiers/villes connus
        known_locations = [
            'abobo', 'yopougon', 'cocody', 'plateau', 'adjamé', 'adjame',
            'marcory', 'treichville', 'koumassi', 'port-bouet', 'port bouet',
            'bingerville', 'anyama', 'angré', 'angre', 'riviera',
            'williamsville', 'attoban', 'palmeraie', 'bassam', 'grand-bassam',
            'mocville', 'mokcville', 'bouaké', 'bouake', 'yamoussoukro',
            'san pedro', 'daloa', 'korhogo', 'man', 'aboisso',
            '2 plateaux', 'deux plateaux', 'zone 4', 'vallon',
        ]

        # Trouver les lieux mentionnés par le client
        mentioned_locations = [loc for loc in known_locations if loc in msg]

        if not mentioned_locations:
            return None

        # Vérifier si le lieu mentionné est DANS l'adresse du marchand
        for loc in mentioned_locations:
            if loc in merchant_address:
                return None  # Le client a raison

        # Le client mentionne un lieu qui N'EST PAS dans l'adresse du marchand
        return merchant_data['address']

    def _is_status_correction(self, msg: str) -> bool:
        """Détecte quand le client conteste un achat prématurément déclaré par le bot."""
        patterns = [
            # Avec accents (après normalisation unicode)
            "j ai rien acheté", "j'ai rien acheté", "j ai pas acheté",
            "j'ai pas acheté", "j ai rien commandé", "j'ai rien commandé",
            "j'ai pas commandé", "j ai pas commandé", "je n ai rien acheté",
            "je n ai pas commandé", "j ai rien décidé", "j ai rien signé",
            "pas encore acheté", "pas encore commandé", "pas encore décidé",
            "on a rien conclu", "on n a pas conclu", "j ai pas dit oui",
            "j'ai pas dit oui", "j ai pas encore dit", "j ai rien dit",
            # Sans accents (comme dans les messages WhatsApp courants)
            "j ai rien achete", "j'ai rien achete", "j ai pas achete",
            "j'ai pas achete", "j ai rien commande", "j'ai rien commande",
            "j'ai pas commande", "j ai pas commande", "je n ai rien achete",
            "je n ai pas commande", "j ai rien decide", "pas encore achete",
            "pas encore commande", "pas encore decide", "j ai rien achet",
            "n ai pas achete", "n ai rien achete",
        ]
        return any(p in msg for p in patterns)

    def _is_hours_question(self, msg: str) -> bool:
        """Détecte une question sur les horaires d'ouverture — patterns précis pour éviter faux positifs"""
        hours_patterns = [
            'horaire', 'ouverture', 'fermeture',
            'quelle heure', 'jusqu a quelle heure', 'a partir de quelle heure',
            'de quel heure', 'ouvert quand', 'quand vous ouvrez', 'quand vous fermez',
            'vous ouvrez a', 'vous fermez a', 'vous etes ouvert',
            'tu es ouvert', 'c est ouvert', 'vous ouvrez', 'vous fermez',
            'ouvert jusqu', 'ferme quand', 'ouvert de',
        ]
        return any(p in msg for p in hours_patterns)

    def _shows_interest(self, msg: str) -> bool:
        """Détecte un intérêt général"""
        interest_keywords = [
            'intéress', 'interesse', 'dispo', 'disponible',
            'photo', 'image', 'voir', 'couleur', 'taille'
        ]
        return any(kw in msg for kw in interest_keywords)
