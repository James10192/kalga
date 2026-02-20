"""
Routes de chat pour KALGA
Gère les conversations entre clients et marchands via WhatsApp
"""
from fastapi import APIRouter, HTTPException, Query, Request, Depends

from ..database import get_db
from ..models.schemas import IncomingMessage, BotResponse
from ..services.chat_service import ChatService, get_chat_service
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
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    Traite un message entrant depuis WhatsApp.
    Délègue au ChatService pour l'orchestration.

    Rate limit: 30 requêtes par minute par IP
    """
    return await chat_service.handle_incoming_message(message)


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
