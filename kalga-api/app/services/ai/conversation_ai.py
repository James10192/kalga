"""
Orchestration de l'IA conversationnelle v4.0
============================================
DeepSeek agentique (function calling) comme chef d'orchestre:

1. DeepSeek reçoit le brief produit + TOOL_DECISION_GUIDE + historique
2. DeepSeek appelle le bon tool (send_photo, send_variants, accept_deal, etc.)
   OU répond en texte libre pour la négociation courante
3. Le code dispatche l'action du tool et valide les règles business
4. Fallback sur conversation_engine si DeepSeek est indisponible
"""

import asyncio
import json
import logging
import time
from typing import Optional, List, Dict, Tuple

from ...database.repositories.knowledge_repo import KnowledgeBaseRepository
from ...database.repositories.client_history_repo import get_client_history_repository

from .conversation_engine import get_conversation_engine
from .deepseek_client import get_deepseek_client, CORRECTION_SYSTEM_PROMPT
from .fallback_responses import FallbackResponses
from .debug_tracer import DebugTracer
from .memory import stm as stm_module
from .memory import ltm as ltm_module
from .memory import episodic as episodic_module
from .tools import TOOLS, TOOL_NAMES
from .detectors import (
    detect_delivery_request,
    detect_pickup_request,
    detect_location_request,
    detect_end_conversation,
    count_low_offers,
    detect_correction_signal
)

logger = logging.getLogger("kalga.ai")

# Préfixe interne pour transporter un tool_call dans le tuple de retour
_TOOL_PREFIX = "__tool__:"


def is_tool_call(response: str) -> bool:
    """Vérifie si une réponse encode un tool_call DeepSeek."""
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


async def generate_response(
    client_message: str,
    product: Dict,
    conversation_history: List[Dict],
    current_offer: Optional[float] = None,
    conversation_status: str = "active",
    negotiation_context: Optional[Dict] = None,
    merchant_data: Optional[Dict] = None,
    tracer: Optional[DebugTracer] = None,
    client_phone: Optional[str] = None
) -> Tuple[Optional[str], Optional[float], bool, str, bool]:
    """
    Génère une réponse via DeepSeek.

    DeepSeek reçoit les 45 derniers messages et décide:
    - Est-ce un deal ?
    - Quel prix a été mentionné ?
    - Faut-il envoyer la localisation ?
    - Quelle réponse envoyer ?

    Le code valide uniquement: prix mentionné >= prix minimum.

    Returns:
        (response_message, new_offer, deal_accepted, new_status, send_location)
    """
    is_first_message = len(conversation_history) <= 1
    min_price = product.get('effective_min_price', product['min_price'])

    # === PRIORITÉ 1: Conversation terminée ===
    if conversation_status == "ended":
        logger.info("Conversation terminée, pas de réponse")
        if tracer:
            tracer.set_mode("ended")
            tracer.event("CHAT", "conversation_ended", reason="status=ended")
        return None, current_offer, True, conversation_status, False

    # === PRIORITÉ 2: États pending (déterministes, pas d'IA nécessaire) ===
    if conversation_status == "pending_pickup":
        if tracer:
            tracer.set_mode("pending_pickup")
            tracer.set_stm(msg_count=len(conversation_history), compressed=False,
                           window=min(len(conversation_history), 8))
        resp, offer, accepted, status = _handle_pending_pickup(client_message, current_offer)
        resend_location = detect_location_request(client_message)
        return resp, offer, accepted, status, resend_location

    if conversation_status == "pending_delivery":
        if tracer:
            tracer.set_mode("pending_delivery")
            tracer.set_stm(msg_count=len(conversation_history), compressed=False,
                           window=min(len(conversation_history), 8))
        resp, offer, accepted, status = _handle_pending_delivery(client_message, current_offer)
        return resp, offer, accepted, status, False

    # === DÉTECTEURS (trace avant priorité 3) ===
    _end_conv = detect_end_conversation(client_message) and not is_first_message
    _correction = detect_correction_signal(client_message) and not is_first_message
    if tracer:
        tracer.set_detector("detect_end_conversation", _end_conv)
        tracer.set_detector("detect_correction_signal", _correction)
        tracer.set_detector("detect_delivery_request", detect_delivery_request(client_message))
        tracer.set_detector("detect_pickup_request", detect_pickup_request(client_message))
        tracer.set_detector("detect_location_request", detect_location_request(client_message))
        tracer.set_detector("is_first_message", is_first_message)

    # === PRIORITÉ 3: Fin de conversation explicite ===
    if _end_conv:
        logger.info(f"Fin de conversation détectée: {client_message[:30]}")
        if tracer:
            tracer.set_mode("end_conversation")
        return None, current_offer, False, "ended", False

    # === AJUSTEMENT FIDÉLITÉ (règle business) ===
    if negotiation_context:
        loyalty_discount = negotiation_context.get('loyalty_discount', 0)
        if loyalty_discount > 0 and negotiation_context.get('is_returning'):
            base_min = product['min_price']
            price_range = product['price'] - base_min
            extra_discount = price_range * (loyalty_discount / 100)
            min_price = max(base_min - extra_discount, base_min * 0.95)
            logger.info(f"Client fidèle: min ajusté à {min_price:,.0f} F")

    # === BASE DE CONNAISSANCES ===
    knowledge_context = await _get_knowledge_context(merchant_data, client_message)
    if tracer:
        tracer.set_kb_results(knowledge_context)
        tracer.add_tool_call(
            "kb_search",
            reason="knowledge base lookup before LLM call",
            args={
                "query": client_message[:100],
                "merchant_id": merchant_data.get('id') if merchant_data else None,
                "results_found": len(knowledge_context) if knowledge_context else 0
            }
        )

    # === DONNÉES MARCHAND ===
    merchant_address = None
    merchant_city = None
    merchant_commune = None
    merchant_quarter = None
    merchant_persona = None

    if merchant_data:
        merchant_address = merchant_data.get('address')
        merchant_city = merchant_data.get('city')
        merchant_commune = merchant_data.get('commune')
        merchant_quarter = merchant_data.get('quarter')

        bot_tone = merchant_data.get('bot_tone')
        bot_style = merchant_data.get('bot_style')
        bot_catchphrase = merchant_data.get('bot_catchphrase')
        if any([bot_tone, bot_style, bot_catchphrase]):
            merchant_persona = {
                'bot_tone': bot_tone or 'casual',
                'bot_style': bot_style or 'flexible',
                'bot_catchphrase': bot_catchphrase,
            }

    # === PRIORITÉ 4: Signal de correction client ===
    # Le client dit explicitement que le bot a répondu à côté → mode correction
    if _correction:
        # Guard anti-boucle : max 2 corrections consécutives, puis redirection marchand
        recent_bot = [m for m in conversation_history[-6:] if not m.get('is_from_client')]
        correction_attempts = sum(
            1 for m in recent_bot
            if "pardon pour la confusion" in m.get('content', '').lower() or
               "dis-moi ta question plus précisément" in m.get('content', '').lower()
        )
        if correction_attempts >= 2:
            logger.info(f"Anti-boucle correction: {correction_attempts} tentatives, redirection marchand")
            return (
                "Pour toute autre question, n'hésite pas à contacter directement le vendeur!",
                current_offer, False, conversation_status, False
            )

        logger.info(f"Signal de correction détecté: {client_message[:50]}")
        if tracer:
            tracer.set_mode("correction")
        deepseek = get_deepseek_client()
        try:
            correction_messages = deepseek.build_correction_messages(
                conversation_history=conversation_history,
                client_correction=client_message,
                product_name=product['name'],
                price=product['price']
            )
            raw = await deepseek.chat_completion(
                messages=correction_messages,
                temperature=0.5,
                max_tokens=400,
                system_prompt=CORRECTION_SYSTEM_PROMPT
            )
            if raw:
                result = deepseek.parse_json_response(raw)
                if result:
                    # Sauvegarder la correction en KB (apprentissage)
                    if result.get('original_question') and result.get('corrected_answer'):
                        try:
                            from ...database.repositories.knowledge_repo import KnowledgeBaseRepository
                            merchant_id = merchant_data.get('id') if merchant_data else None
                            if merchant_id:
                                kb_repo = KnowledgeBaseRepository()
                                await kb_repo.save_entry(
                                    merchant_id=merchant_id,
                                    question=result['original_question'],
                                    answer=result['corrected_answer'],
                                    source="client_correction"
                                )
                                logger.info(f"Correction sauvegardée en KB: {result['original_question'][:50]}")
                        except Exception as e:
                            logger.debug(f"Sauvegarde correction KB (non bloquant): {e}")
                    return (
                        result['response'],
                        current_offer,
                        False,
                        conversation_status,
                        result.get('send_location', False)
                    )
        except Exception as e:
            logger.warning(f"Erreur mode correction: {e}")
        # Fallback correction si DeepSeek échoue
        return (
            "Pardon pour la confusion! Dis-moi ta question plus précisément et je te réponds correctement.",
            current_offer, False, conversation_status, False
        )

    # === STM: compression historique ===
    merchant_id = merchant_data.get('id') if merchant_data else None
    deepseek = get_deepseek_client()

    stm_summary, stm_recent = await stm_module.build_context(
        history=conversation_history,
        deepseek_client=deepseek
    )
    stm_compressed = stm_summary is not None
    if tracer:
        tracer.set_stm(
            msg_count=len(conversation_history),
            compressed=stm_compressed,
            window=len(stm_recent)
        )
    if stm_compressed:
        logger.info(f"STM: {len(conversation_history)} msgs compressés, fenêtre={len(stm_recent)}")

    # === EPISODIC: contexte inter-sessions ===
    episodic_context = None
    if client_phone and merchant_id and not is_first_message:
        try:
            client_history_repo = get_client_history_repository()
            episodic_context = await episodic_module.get_episodic_context(
                repo=client_history_repo,
                merchant_id=merchant_id,
                client_phone=client_phone,
                product_name=product.get('name', '')
            )
            if tracer:
                facts = await client_history_repo.get_memory_facts(merchant_id, client_phone) or []
                summaries = await client_history_repo.get_conversation_summaries(merchant_id, client_phone) or []
                tracer.set_episodic(sessions=summaries[:3], fact_count=len(facts))
                if episodic_context:
                    tracer.event("MEMORY", "episodic_injected", sessions=len(summaries))
        except Exception as e:
            logger.debug(f"Episodic context skipped: {e}")

    # === APPEL DEEPSEEK ===
    if tracer:
        tracer.set_mode("deepseek")

    try:
        image_path = product.get('image_path')
        has_image = bool(image_path)
        image_url = f"/uploads/{image_path}" if image_path else None

        system_prompt, user_message = deepseek.build_agentic_messages(
            product_name=product['name'],
            price=product['price'],
            min_price=min_price,
            conversation_history=conversation_history,
            client_message=client_message,
            is_first_message=is_first_message,
            product_description=product.get('description'),
            variants=product.get('variants') or [],
            merchant_address=merchant_address,
            merchant_city=merchant_city,
            merchant_commune=merchant_commune,
            merchant_quarter=merchant_quarter,
            merchant_persona=merchant_persona,
            knowledge_context=knowledge_context,
            conversation_status=conversation_status,
            current_offer=current_offer,
            episodic_context=episodic_context,
            stm_summary=stm_summary,
            stm_recent=stm_recent,
        )

        _t0 = time.time()
        agentic_result = await deepseek.agentic_completion(
            system_prompt=system_prompt,
            user_message=user_message,
            tools=TOOLS,
            temperature=0.7,
            max_tokens=500
        )
        _latency = (time.time() - _t0) * 1000

        if tracer:
            tracer.set_llm_call(
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}],
                raw_response=str(agentic_result) if agentic_result else None,
                parsed=agentic_result,
                latency_ms=_latency
            )

    except Exception as e:
        logger.warning(f"Erreur appel DeepSeek agentique: {e}")
        if tracer:
            tracer.event("LLM", "deepseek_error", error=str(e))
        agentic_result = None

    # === FALLBACK si DeepSeek échoue ===
    if not agentic_result:
        logger.info("DeepSeek indisponible — fallback sur conversation_engine")
        if tracer:
            tracer.set_fallback("deepseek_unavailable")
        return await _fallback_to_engine(
            client_message=client_message,
            product=product,
            conversation_history=conversation_history,
            current_offer=current_offer,
            conversation_status=conversation_status,
            is_first_message=is_first_message,
            merchant_data=merchant_data
        )

    # === TOOL CALL : DeepSeek a choisi une action ===
    if agentic_result["type"] == "tool_call":
        name = agentic_result["name"]
        args = agentic_result["args"]

        if name not in TOOL_NAMES:
            logger.warning(f"Tool inconnu retourné par DeepSeek: {name}")
            return await _fallback_to_engine(
                client_message=client_message,
                product=product,
                conversation_history=conversation_history,
                current_offer=current_offer,
                conversation_status=conversation_status,
                is_first_message=is_first_message,
                merchant_data=merchant_data
            )

        logger.info(f"DeepSeek tool_call: {name}({args})")

        # Garde-fou : si accept_deal avec prix < min → rejeter
        if name == "accept_deal":
            offered = args.get("price") or current_offer
            if offered and offered < min_price:
                logger.warning(
                    f"accept_deal rejeté: {offered} < min {min_price} — converti en counter_offer"
                )
                min_f = f"{int(min_price):,}".replace(",", " ")
                price_f = f"{int(offered):,}".replace(",", " ")
                counter_msg = f"{price_f} F c'est un peu bas! Je peux faire {min_f} F, c'est mon dernier prix."
                return counter_msg, offered, False, "negotiating", False

        # Retourner le tool_call encodé — chat_service dispatch et exécute
        encoded = f"{_TOOL_PREFIX}{name}:{json.dumps(args, ensure_ascii=False)}"
        return encoded, current_offer, False, conversation_status, False

    # === TEXTE LIBRE : réponse normale de négociation ===
    response = agentic_result.get("content", "").strip()
    if not response:
        logger.warning("DeepSeek agentic a retourné un texte vide — fallback")
        return await _fallback_to_engine(
            client_message=client_message,
            product=product,
            conversation_history=conversation_history,
            current_offer=current_offer,
            conversation_status=conversation_status,
            is_first_message=is_first_message,
            merchant_data=merchant_data
        )

    logger.info(f"DeepSeek text: {response[:80]}...")

    # Statut : progresser si une offre est mentionnée dans la réponse
    if conversation_status in ("active", "negotiating"):
        new_status = "negotiating"
    else:
        new_status = conversation_status

    if tracer:
        tracer.event(
            "BUSINESS", "status_determined",
            old_status=conversation_status,
            new_status=new_status
        )

    # === LTM: extraction faits à la fin de conversation (non-bloquant) ===
    conversation_ended = new_status in ("pending_delivery", "pending_pickup", "ended", "agreed")
    if conversation_ended and client_phone and merchant_id and conversation_history:
        try:
            client_history_repo = get_client_history_repository()
            asyncio.create_task(ltm_module.extract_and_save(
                repo=client_history_repo,
                merchant_id=merchant_id,
                client_phone=client_phone,
                history=conversation_history,
                product=product,
                outcome="ended",
                deepseek_client=deepseek
            ))
            if tracer:
                tracer.event("MEMORY", "ltm_extraction_scheduled",
                    history_len=len(conversation_history))
                existing_facts = await client_history_repo.get_memory_facts(merchant_id, client_phone) or []
                existing_prefs = await client_history_repo.get_preferences(merchant_id, client_phone)
                tracer.set_ltm(facts=existing_facts, preferences=existing_prefs)
        except Exception as e:
            logger.debug(f"LTM scheduling skipped: {e}")
    elif tracer and client_phone and merchant_id:
        try:
            client_history_repo = get_client_history_repository()
            existing_facts = await client_history_repo.get_memory_facts(merchant_id, client_phone) or []
            existing_prefs = await client_history_repo.get_preferences(merchant_id, client_phone)
            tracer.set_ltm(facts=existing_facts, preferences=existing_prefs)
        except Exception as e:
            logger.debug(f"LTM snapshot skipped: {e}")

    return response, current_offer, False, new_status, False


# =============================================================================
# FONCTIONS UTILITAIRES
# =============================================================================

async def _get_knowledge_context(
    merchant_data: Optional[Dict],
    client_message: str
) -> Optional[List[str]]:
    """Recherche dans la base de connaissances du marchand."""
    merchant_id = merchant_data.get('id') if merchant_data else None
    if not merchant_id:
        return None
    try:
        kb_repo = KnowledgeBaseRepository()
        kb_results = await kb_repo.search(
            merchant_id=merchant_id,
            query=client_message,
            limit=3
        )
        if kb_results:
            return [
                f"Q: {entry['question']} → R: {entry['answer']}"
                for entry in kb_results
            ]
    except Exception as e:
        logger.debug(f"KB search skipped: {e}")
    return None


async def _fallback_to_engine(
    client_message: str,
    product: Dict,
    conversation_history: List[Dict],
    current_offer: Optional[float],
    conversation_status: str,
    is_first_message: bool,
    merchant_data: Optional[Dict] = None
) -> Tuple[Optional[str], Optional[float], bool, str, bool]:
    """
    Fallback sur conversation_engine (moteur keywords) si DeepSeek est indisponible.
    Garantit la haute disponibilité du système.
    """
    try:
        engine = get_conversation_engine()
        result = await engine.process_message(
            client_message=client_message,
            product=product,
            conversation_history=conversation_history,
            current_state=conversation_status,
            current_offer=current_offer,
            merchant_data=merchant_data
        )
        return (
            result["response"],
            result["new_offer"],
            result["deal_accepted"],
            result["new_state"],
            result["send_location"]
        )
    except Exception as e:
        logger.error(f"Fallback engine aussi en erreur: {e}")
        # Dernier recours: FallbackResponses statiques
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
        send_location = detect_location_request(client_message)
        return response, offer, accepted, status, send_location


def _handle_pending_pickup(
    client_message: str,
    current_offer: Optional[float]
) -> Tuple[str, Optional[float], bool, str]:
    """Gère les messages quand le client a confirmé passage en magasin."""
    import random
    msg_lower = client_message.lower()

    if detect_location_request(msg_lower):
        return "Je te renvoie la localisation tout de suite !", current_offer, True, "pending_pickup"

    if any(kw in msg_lower for kw in ['ok', 'oui', 'merci', "d'accord", 'attends', "j'attends", 'vu', 'bien', 'super', 'parfait']):
        responses = [
            "A tout a l'heure alors !",
            "On t'attend !",
            "Parfait, a bientot !"
        ]
        return random.choice(responses), current_offer, True, "pending_pickup"

    return "Pour plus d'infos, le vendeur te repond directement !", current_offer, True, "pending_pickup"


def _handle_pending_delivery(
    client_message: str,
    current_offer: Optional[float]
) -> Tuple[str, Optional[float], bool, str]:
    """Gère les messages quand le client attend la livraison."""
    import random
    msg_lower = client_message.lower()

    if any(kw in msg_lower for kw in ['ok', 'oui', 'merci', "d'accord", 'attends', "j'attends", 'bien', 'super', 'parfait']):
        responses = [
            "Parfait ! Le vendeur te contacte pour la livraison.",
            "C'est note, on te rappelle tres vite !",
            "Top ! Tu seras contacte rapidement."
        ]
        return random.choice(responses), current_offer, True, "pending_delivery"

    return "Le vendeur te contacte pour finaliser la livraison !", current_offer, True, "pending_delivery"


def _analyze_conversation_health(
    conversation_history: List[Dict],
    client_message: str,
    product: Dict
) -> Dict:
    """
    Analyse la santé conversationnelle pour la boucle d'apprentissage autonome.
    Utilisée par chat_service.py pour auto-flaguer les questions sans réponse.
    """
    import re

    health = {
        "is_looping": False,
        "unanswered_question": False,
        "last_unanswered": None,
        "summary": []
    }

    if len(conversation_history) < 2:
        return health

    recent = conversation_history[-6:] if len(conversation_history) >= 6 else conversation_history
    bot_messages = [m['content'] for m in recent if not m.get('is_from_client')]
    price = product['price']
    price_str_variants = [
        f"{int(price):,}".replace(",", " "),
        str(int(price)),
    ]

    # Détection de boucle
    if len(bot_messages) >= 2:
        for variant in price_str_variants:
            occurrences = sum(1 for bm in bot_messages if variant in bm)
            if occurrences >= 2:
                health["is_looping"] = True
                health["summary"].append(
                    f"BOUCLE DÉTECTÉE: prix {variant} F répété {occurrences} fois"
                )
                break

    # Détection de question sans réponse
    if len(recent) >= 3:
        last_bot_idx = None
        for i in range(len(recent) - 1, -1, -1):
            if not recent[i].get('is_from_client'):
                last_bot_idx = i
                break

        if last_bot_idx is not None and last_bot_idx > 0:
            client_before = [m for m in recent[:last_bot_idx] if m.get('is_from_client')]
            if client_before:
                last_q = client_before[-1]['content']
                if '?' in last_q:
                    last_bot = recent[last_bot_idx]['content'].lower()
                    seems_ignored = (
                        len(last_bot.split()) < 15 and
                        any(v in last_bot for v in price_str_variants)
                    )
                    if seems_ignored:
                        health["unanswered_question"] = True
                        health["last_unanswered"] = last_q
                        health["summary"].append(
                            f"QUESTION IGNORÉE: \"{last_q[:60]}\""
                        )

    return health


# Alias public pour import depuis chat_service (boucle d'apprentissage autonome)
analyze_conversation_health = _analyze_conversation_health


# Exports de compatibilité — utilisés par conversation.py compat layer
def extract_product_code(text: str) -> Optional[str]:
    import re
    match = re.search(r'#K\d{3}', text, re.IGNORECASE)
    return match.group(0).upper() if match else None


def extract_price_offer(text: str) -> Optional[float]:
    import re
    k_match = re.search(r'(\d+)\s*k\b', text.lower())
    if k_match:
        return float(k_match.group(1)) * 1000
    space_match = re.search(r'(\d{1,3}(?:\s\d{3})+)', text)
    if space_match:
        return float(space_match.group(1).replace(' ', ''))
    simple_match = re.search(r'\b(\d{4,})\b', text)
    if simple_match:
        return float(simple_match.group(1))
    return None
