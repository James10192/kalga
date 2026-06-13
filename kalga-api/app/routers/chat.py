"""
Routes de chat pour KALGA
Gère les conversations entre clients et marchands via WhatsApp
"""
from fastapi import APIRouter, HTTPException, Query, Request, Depends, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional, List

from ..database import get_db
from ..database.repositories.knowledge_repo import KnowledgeBaseRepository
from ..database.repositories.merchant_repo import MerchantRepository
from ..database.repositories.product_repo import ProductRepository
from ..database.repositories.client_history_repo import get_client_history_repository
from ..models.schemas import IncomingMessage, BotResponse, DebugIncomingMessage, DebugBotResponse, MerchantReply
from ..services.chat_service import ChatService, get_chat_service
from ..services.ai.debug_tracer import DebugTracer
from ..dependencies import verify_internal_key
from ..rate_limiter import limiter
import logging

router = APIRouter(prefix="/chat", tags=["Conversations"])
logger = logging.getLogger("kalga.chat")

# Constantes de pagination
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


@router.post("/incoming", response_model=BotResponse)
@limiter.limit("30/minute")
async def handle_incoming_message(
    request: Request,
    message: IncomingMessage,
    chat_service: ChatService = Depends(get_chat_service),
    _: None = Depends(verify_internal_key),
):
    """
    Traite un message entrant depuis WhatsApp.
    Délègue au ChatService pour l'orchestration.

    Sécurité: exige le header `X-Internal-Key` (verrou bridge <-> API).
    Rate limit: 30 requêtes par minute par IP
    """
    return await chat_service.handle_incoming_message(message)


@router.post("/incoming-media", response_model=DebugBotResponse)
@limiter.limit("20/minute")
async def handle_incoming_media(
    request: Request,
    merchant_phone: str = Form(...),
    client_phone: str = Form(...),
    client_name: str = Form(""),
    media_type: str = Form(...),
    file: UploadFile = File(...),
    chat_service: ChatService = Depends(get_chat_service),
    _: None = Depends(verify_internal_key),
):
    """
    Traite un message média (note vocale ou image) depuis WhatsApp.
    - audio: transcription via faster-whisper → pipeline texte
    - image: recherche visuelle CLIP → pipeline texte
    """
    file_bytes = await file.read()

    if media_type == "audio":
        from ..services.transcription_service import transcribe_voice_note
        text, lang = await transcribe_voice_note(file_bytes)
        if not text or len(text.split()) < 2:
            message_text = "[🎤 Vocal incompréhensible. Demande gentiment au client de réécrire en texte.]"
        else:
            message_text = f"[🎤 Vocal transcrit ({lang})]: {text}"

    elif media_type == "image":
        import asyncio
        from ..services.visual_search_service import compute_image_embedding, find_similar_products
        merchant_repo = MerchantRepository()
        merchant = await merchant_repo.get_by_phone(merchant_phone)
        if not merchant:
            raise HTTPException(status_code=404, detail="Marchand introuvable")

        product_repo = ProductRepository()
        # Exécuter en thread pool — CLIP est synchrone et bloquant
        loop = asyncio.get_running_loop()
        query_emb = await loop.run_in_executor(None, compute_image_embedding, file_bytes)

        if query_emb is None:
            message_text = "[📸 Le client a envoyé une photo. Présente-lui les produits disponibles ou demande-lui de décrire ce qu'il cherche.]"
        else:
            product_embeddings = await product_repo.get_all_with_embeddings(merchant["id"])
            matches = find_similar_products(query_emb, product_embeddings)
            if matches:
                best = matches[0]
                if len(matches) == 1 or best["score"] - matches[1]["score"] >= 0.08:
                    # Un seul match clair — présenter directement ce produit
                    price_str = f"{int(best['price']):,} F".replace(",", " ") if best["price"] else "prix à demander"
                    desc_str = f" — {best['description'][:80]}" if best["description"] else ""
                    message_text = (
                        f"[📸 Recherche visuelle — produit identifié: {best['code']} \"{best['name']}\" "
                        f"à {price_str}{desc_str}. Présente ce produit au client et propose-le-lui directement.]"
                    )
                else:
                    # Plusieurs candidats proches — donner tous les détails pour que l'IA choisisse
                    lines = []
                    for m in matches:
                        price_str = f"{int(m['price']):,} F".replace(",", " ") if m["price"] else "prix ?"
                        desc_str = f", {m['description'][:60]}" if m["description"] else ""
                        lines.append(f"  • {m['code']} \"{m['name']}\" à {price_str}{desc_str} (similarité {m['score']:.0%})")
                    message_text = (
                        "[📸 Recherche visuelle — plusieurs produits similaires trouvés:\n"
                        + "\n".join(lines)
                        + f"\nChoisis le plus probable selon les descriptions et présente-le directement au client. "
                        f"Ne demande pas de clarification — le meilleur match visuel est {matches[0]['code']}.]"
                    )
            else:
                message_text = "[📸 Le client a envoyé une photo d'un produit introuvable dans le catalogue. Explique-lui poliment que tu n'as pas ce produit et propose les alternatives disponibles.]"
    else:
        raise HTTPException(status_code=400, detail=f"media_type '{media_type}' non supporté")

    from ..services.ai.debug_tracer import DebugTracer
    incoming = IncomingMessage(
        merchant_phone=merchant_phone,
        client_phone=client_phone,
        client_name=client_name or None,
        message=message_text,
    )
    tracer = DebugTracer()
    response = await chat_service.handle_incoming_message(incoming, tracer=tracer)
    tracer.finalize()
    return DebugBotResponse(
        **response.model_dump(),
        debug_trace=tracer.to_dict()
    )


@router.post("/test-incoming", response_model=DebugBotResponse, tags=["Debug"])
async def handle_test_incoming_message(
    message: DebugIncomingMessage,
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    Endpoint de test — même flux que /incoming mais avec trace complète du pipeline AI.
    Pas de rate limit. Usage: développement et debug uniquement.
    """
    tracer = DebugTracer()
    response = await chat_service.handle_incoming_message(message, tracer=tracer)
    tracer.finalize()
    return DebugBotResponse(
        **response.model_dump(),
        debug_trace=tracer.to_dict()
    )


@router.get("/conversations/{merchant_phone}")
async def get_merchant_conversations(
    merchant_phone: str,
    status: str = "active",
    page: int = Query(1, ge=1, description="Numéro de page"),
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Éléments par page"),
    chat_service: ChatService = Depends(get_chat_service)
):
    """Liste les conversations d'un marchand avec pagination"""
    conversations = await chat_service.get_conversations(merchant_phone, status)

    if conversations is None:
        raise HTTPException(status_code=404, detail="Marchand non trouvé")

    # Pagination
    total = len(conversations)
    start = (page - 1) * limit
    end = start + limit
    paginated = conversations[start:end]

    return {
        "merchant_phone": merchant_phone,
        "status": status,
        "conversations": paginated,
        "page": page,
        "limit": limit,
        "total": total,
        "pages": (total + limit - 1) // limit if total > 0 else 0
    }


@router.get("/conversations/{conv_id}/messages")
async def get_conversation_messages(
    conv_id: int,
    chat_service: ChatService = Depends(get_chat_service)
):
    """Récupère les messages d'une conversation"""
    messages = await chat_service.get_conversation_messages(conv_id)

    if messages is None:
        raise HTTPException(status_code=404, detail="Conversation non trouvée")

    return {
        "conversation_id": conv_id,
        "messages": messages,
        "count": len(messages)
    }


@router.post("/conversations/{conv_id}/accept")
async def accept_conversation_offer(conv_id: int):
    """Accepte l'offre du client et marque la conversation comme complétée"""
    db = await get_db()

    conversation = await db.get_conversation_by_id(conv_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation non trouvée")

    await db.update_conversation(conv_id, status="completed")

    return {
        "success": True,
        "message": "Offre acceptée, conversation terminée",
        "final_price": conversation.get('current_offer')
    }


@router.post("/conversations/{conv_id}/reject")
async def reject_conversation_offer(conv_id: int):
    """Rejette l'offre du client (conversation reste active)"""
    db = await get_db()

    conversation = await db.get_conversation_by_id(conv_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation non trouvée")

    await db.update_conversation(conv_id, current_offer=None)

    return {
        "success": True,
        "message": "Offre rejetée, conversation toujours active"
    }


@router.post("/cleanup")
async def cleanup_old_conversations():
    """Nettoie les conversations expirées (7+ jours)"""
    db = await get_db()
    count = await db.cleanup_expired_conversations(days=7)
    return {
        "success": True,
        "message": "Conversations expirées nettoyées",
        "cleaned": count
    }


# =============================================================================
# ENDPOINTS BASE DE CONNAISSANCES
# =============================================================================

class KnowledgeEntryCreate(BaseModel):
    merchant_phone: str
    question: str        # Question du client
    answer: str          # Réponse donnée par le marchand
    source: str = "human_reply"


@router.post("/knowledge")
async def add_knowledge_entry(entry: KnowledgeEntryCreate):
    """
    Ajoute une entrée dans la base de connaissances du marchand.

    Appelé par le Dashboard quand le marchand répond manuellement
    à un client. La réponse est mémorisée pour enrichir les futures
    réponses automatiques sur des questions similaires.
    """
    merchant_repo = MerchantRepository()
    merchant = await merchant_repo.get_by_phone(entry.merchant_phone)
    if not merchant:
        raise HTTPException(status_code=404, detail="Marchand non trouvé")

    kb_repo = KnowledgeBaseRepository()
    entry_id = await kb_repo.save_entry(
        merchant_id=merchant['id'],
        question=entry.question,
        answer=entry.answer,
        source=entry.source
    )

    logger.info(
        f"KB: entrée #{entry_id} ajoutée pour marchand {entry.merchant_phone} "
        f"— Q: {entry.question[:50]}"
    )

    return {
        "success": True,
        "entry_id": entry_id,
        "message": "Réponse enregistrée dans la base de connaissances"
    }


@router.get("/knowledge/{merchant_phone}/insights")
async def get_knowledge_insights(merchant_phone: str):
    """
    Statistiques de la boucle d'apprentissage pour le Dashboard marchand.

    Retourne:
    - Répartition des entrées KB par source (default_faq, auto_learned_deal, feedback_correction…)
    - Top 5 entrées KB les plus utilisées
    - Questions auto-flaggées (sans réponse bot adéquate), groupées par fréquence
    - Compteurs agrégés (auto_learned_deals, feedback_corrections, gap_count)
    """
    merchant_repo = MerchantRepository()
    merchant = await merchant_repo.get_by_phone(merchant_phone)
    if not merchant:
        raise HTTPException(status_code=404, detail="Marchand non trouvé")

    kb_repo = KnowledgeBaseRepository()
    insights = await kb_repo.get_insights(merchant['id'])
    return {"merchant_phone": merchant_phone, **insights}


@router.get("/knowledge/{merchant_phone}")
async def get_knowledge_entries(
    merchant_phone: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """
    Récupère la base de connaissances d'un marchand (pour affichage Dashboard).
    Triée par usage décroissant — les réponses les plus utilisées en premier.
    """
    merchant_repo = MerchantRepository()
    merchant = await merchant_repo.get_by_phone(merchant_phone)
    if not merchant:
        raise HTTPException(status_code=404, detail="Marchand non trouvé")

    kb_repo = KnowledgeBaseRepository()
    entries = await kb_repo.get_all(
        merchant_id=merchant['id'],
        limit=limit,
        offset=offset
    )

    return {
        "merchant_phone": merchant_phone,
        "entries": entries,
        "count": len(entries)
    }


@router.delete("/knowledge/{entry_id}")
async def delete_knowledge_entry(entry_id: int, merchant_phone: str = Query(...)):
    """Supprime une entrée de la base de connaissances"""
    merchant_repo = MerchantRepository()
    merchant = await merchant_repo.get_by_phone(merchant_phone)
    if not merchant:
        raise HTTPException(status_code=404, detail="Marchand non trouvé")

    kb_repo = KnowledgeBaseRepository()
    deleted = await kb_repo.delete_entry(entry_id=entry_id, merchant_id=merchant['id'])

    if not deleted:
        raise HTTPException(status_code=404, detail="Entrée non trouvée ou accès refusé")

    return {"success": True, "message": "Entrée supprimée"}


# =============================================================================
# HUMAN TAKEOVER — Réponse manuelle du marchand
# =============================================================================

@router.post("/merchant-reply", tags=["Debug"])
async def merchant_reply(reply: MerchantReply):
    """
    Enregistre la réponse manuelle du marchand (human takeover).

    Quand l'IA ne peut pas répondre correctement (ex: localisation non configurée,
    question hors scope), le marchand prend la main et répond manuellement.
    Si save_to_kb=True (défaut), la paire Q/R est sauvegardée en KB automatiquement
    pour que l'IA apprenne à répondre seule aux prochains clients.
    """
    kb_entry_id = None
    if reply.save_to_kb and reply.client_question.strip() and reply.merchant_answer.strip():
        kb_repo = KnowledgeBaseRepository()
        kb_entry_id = await kb_repo.save_entry(
            merchant_id=reply.merchant_id,
            question=reply.client_question.strip(),
            answer=reply.merchant_answer.strip(),
            source="human_reply"
        )
        logger.info(
            f"Human takeover → KB: entrée #{kb_entry_id} pour merchant_id={reply.merchant_id} "
            f"— Q: {reply.client_question[:50]}"
        )

    return {
        "success": True,
        "kb_entry_id": kb_entry_id,
        "message": "Réponse enregistrée" + (" et apprise en KB" if kb_entry_id else "")
    }


# =============================================================================
# BULK FAQ IMPORT
# =============================================================================

class BulkKnowledgeEntry(BaseModel):
    question: str
    answer: str


class BulkKnowledgeImport(BaseModel):
    merchant_phone: str
    entries: List[BulkKnowledgeEntry]


@router.post("/knowledge/bulk")
async def bulk_import_knowledge(bulk: BulkKnowledgeImport):
    """
    Importe une liste de paires Q/R dans la base de connaissances du marchand.

    Permet aux marchands d'alimenter leur KB en une seule requête
    (ex: importer leur FAQ existante, leurs réponses types, etc.)
    """
    merchant_repo = MerchantRepository()
    merchant = await merchant_repo.get_by_phone(bulk.merchant_phone)
    if not merchant:
        raise HTTPException(status_code=404, detail="Marchand non trouvé")

    if not bulk.entries:
        raise HTTPException(status_code=400, detail="Aucune entrée à importer")

    if len(bulk.entries) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 entrées par import")

    kb_repo = KnowledgeBaseRepository()
    created_ids = []
    errors = []

    for i, entry in enumerate(bulk.entries):
        if not entry.question.strip() or not entry.answer.strip():
            errors.append(f"Entrée #{i+1}: question ou réponse vide ignorée")
            continue
        try:
            entry_id = await kb_repo.save_entry(
                merchant_id=merchant['id'],
                question=entry.question.strip(),
                answer=entry.answer.strip(),
                source="bulk_import"
            )
            created_ids.append(entry_id)
        except Exception as e:
            errors.append(f"Entrée #{i+1}: erreur ({str(e)[:50]})")

    logger.info(
        f"KB bulk import: {len(created_ids)} entrées créées pour {bulk.merchant_phone}"
    )

    return {
        "success": True,
        "created": len(created_ids),
        "errors": len(errors),
        "error_details": errors if errors else None,
        "message": f"{len(created_ids)} entrées importées dans la base de connaissances"
    }


# =============================================================================
# BOUCLE D'APPRENTISSAGE TERRAIN — Feedback marchand
# =============================================================================

class ConversationFeedback(BaseModel):
    merchant_phone: str
    client_phone: str
    client_message: str
    bot_response: str
    feedback_type: str = "bad_response"   # "bad_response" | "good_response"
    notes: Optional[str] = None
    corrected_answer: Optional[str] = None  # Bonne réponse (auto-sauvée en KB si fournie)


@router.post("/conversations/{conv_id}/feedback")
async def add_conversation_feedback(conv_id: int, feedback: ConversationFeedback):
    """
    Enregistre un feedback du marchand sur une réponse du bot.

    Workflow:
    1. Le marchand voit une mauvaise réponse dans le Dashboard
    2. Il clique "Mauvaise réponse" et saisit la bonne réponse
    3. Le feedback est enregistré + la bonne réponse est sauvée en KB automatiquement

    Si corrected_answer fournie → la paire (client_message → corrected_answer)
    est automatiquement sauvegardée dans la base de connaissances du marchand.
    """
    if feedback.feedback_type not in ("bad_response", "good_response"):
        raise HTTPException(
            status_code=400,
            detail="feedback_type doit être 'bad_response' ou 'good_response'"
        )

    merchant_repo = MerchantRepository()
    merchant = await merchant_repo.get_by_phone(feedback.merchant_phone)
    if not merchant:
        raise HTTPException(status_code=404, detail="Marchand non trouvé")

    merchant_id = merchant['id']
    kb_entry_id = None

    # Auto-sauvegarde en KB si corrected_answer fourni pour une bad_response
    if feedback.feedback_type == "bad_response" and feedback.corrected_answer:
        corrected = feedback.corrected_answer.strip()
        if corrected:
            kb_repo = KnowledgeBaseRepository()
            kb_entry_id = await kb_repo.save_entry(
                merchant_id=merchant_id,
                question=feedback.client_message,
                answer=corrected,
                source="feedback_correction"
            )
            logger.info(
                f"Feedback→KB: entrée #{kb_entry_id} créée "
                f"pour marchand {feedback.merchant_phone}"
            )

    # Enregistrer le feedback dans la table dédiée (Convex)
    from ..infrastructure.convex_client import get_convex
    fb_args = {
        "conversationId": conv_id,
        "merchantId": merchant_id,
        "clientPhone": feedback.client_phone,
        "clientMessage": feedback.client_message,
        "botResponse": feedback.bot_response,
        "feedbackType": feedback.feedback_type,
    }
    if feedback.notes is not None:
        fb_args["notes"] = feedback.notes
    if kb_entry_id is not None:
        fb_args["kbEntryId"] = kb_entry_id
    fb_result = await get_convex().mutation("internal/conversation:addFeedback", fb_args)
    feedback_id = fb_result.get("feedbackId") if fb_result else None

    result = {
        "success": True,
        "feedback_id": feedback_id,
        "message": "Feedback enregistré"
    }
    if kb_entry_id:
        result["kb_entry_id"] = kb_entry_id
        result["message"] += " et réponse corrigée ajoutée à la base de connaissances"

    return result


@router.get("/debug/ltm", tags=["Debug"])
async def get_ltm_snapshot(
    merchant_id: int = Query(..., description="ID du marchand"),
    client_phone: str = Query(..., description="Téléphone du client")
):
    """
    Retourne l'état actuel de la LTM pour un client/marchand donné.
    Utilisé par le dashboard de debug pour rafraîchir après extraction async.
    """
    repo = get_client_history_repository()
    facts = await repo.get_memory_facts(merchant_id, client_phone) or []
    prefs = await repo.get_preferences(merchant_id, client_phone)
    return {
        "fact_count": len(facts),
        "facts": facts,
        "preferences": prefs
    }
