"""
Routes HTTP pour les commandes marchand
Simplifié: délègue tout au service
"""
from fastapi import APIRouter, Depends
import logging

from .schemas import MerchantMessage, CommandResponse
from .service import MerchantCommandService, get_merchant_command_service

logger = logging.getLogger("kalga.routes.merchant")

router = APIRouter(prefix="/merchant", tags=["Commandes Marchand"])


@router.post("/command", response_model=CommandResponse)
async def handle_merchant_command(
    msg: MerchantMessage,
    service: MerchantCommandService = Depends(get_merchant_command_service)
) -> CommandResponse:
    """
    Traite une commande WhatsApp du marchand.

    Commandes supportées:
    - **produit**: Démarre la création d'un produit
    - **modifier #K001**: Modifie un produit existant
    - **variante #K001**: Ajoute une variante à un produit
    - **mes produits**: Liste les produits
    - **supprimer #K001**: Désactive un produit
    - **!ok** / **!livré**: Marque une vente comme terminée
    - **!annuler**: Annule une vente en attente
    - **aide**: Affiche l'aide
    """
    logger.info(f"POST /merchant/command: {msg.merchant_phone}")
    return await service.process_command(msg)
