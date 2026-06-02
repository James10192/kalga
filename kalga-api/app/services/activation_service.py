"""
Service de gestion des activations marchands
Gère la génération de codes et l'envoi via WhatsApp
"""
import httpx
from typing import Optional
from datetime import datetime, timedelta

from ..config import settings
from ..database.repositories import (
    get_activation_repository,
    get_subscription_repository,
    get_merchant_repository
)


class ActivationService:
    """Service pour l'activation des abonnements marchands"""

    def __init__(self):
        self.activation_repo = get_activation_repository()
        self.subscription_repo = get_subscription_repository()
        self.merchant_repo = get_merchant_repository()
        self.whatsapp_url = settings.whatsapp_bridge_url

    async def generate_and_send_code(self, merchant_id: int, admin_id: int) -> dict:
        """
        Génère un code d'activation et l'envoie au marchand via WhatsApp.

        Args:
            merchant_id: ID du marchand
            admin_id: ID de l'admin qui valide

        Returns:
            dict avec success, code, message
        """
        # Récupérer les infos du marchand
        merchant = await self.merchant_repo.get_by_id(merchant_id)
        if not merchant:
            return {
                "success": False,
                "message": "Marchand introuvable"
            }

        # Générer le code
        code_info = await self.activation_repo.create_code(merchant_id, admin_id)

        # Envoyer via WhatsApp
        whatsapp_message = self._format_activation_message(code_info["code"])

        try:
            send_result = await self._send_whatsapp_message(
                merchant["phone"],
                whatsapp_message
            )

            if send_result["success"]:
                return {
                    "success": True,
                    "code": code_info["code"],
                    "expires_at": code_info["expires_at"],
                    "message": f"Code envoyé à {merchant['phone']}"
                }
            else:
                return {
                    "success": False,
                    "code": code_info["code"],
                    "message": f"Code généré mais erreur d'envoi WhatsApp: {send_result.get('error', 'Erreur inconnue')}"
                }

        except Exception as e:
            return {
                "success": False,
                "code": code_info["code"],
                "message": f"Code généré mais erreur d'envoi: {str(e)}"
            }

    def _format_activation_message(self, code: str) -> str:
        """Formate le message d'activation pour WhatsApp"""
        return f"""🎉 *Bienvenue sur KALGA!*

Votre code d'activation:

*{code}*

📱 Entrez ce code dans l'application pour activer votre compte.

⏰ Ce code expire dans 24 heures.

Besoin d'aide? Contactez-nous!"""

    async def _send_whatsapp_message(self, phone: str, message: str) -> dict:
        """Envoie un message via le bridge WhatsApp"""
        try:
            headers = {}
            if getattr(settings, 'internal_api_key', ''):
                headers["X-Internal-Key"] = settings.internal_api_key
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.whatsapp_url}/send",
                    json={
                        "merchant_phone": phone,
                        "to": phone,
                        "message": message
                    },
                    headers=headers,
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("success"):
                        return {"success": True}
                    else:
                        return {"success": False, "error": data.get("error", "Echec envoi")}
                elif response.status_code == 503:
                    return {"success": False, "error": "WhatsApp non connecte. Le marchand doit scanner le QR code."}
                else:
                    return {"success": False, "error": f"Erreur {response.status_code}: {response.text}"}

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def verify_code(self, code: str, merchant_phone: str) -> dict:
        """
        Vérifie un code d'activation et active l'abonnement si valide.

        Returns:
            dict avec success, message
        """
        # Valider le code
        result = await self.activation_repo.validate_code(code, merchant_phone)

        if not result["success"]:
            return result

        # Activer l'abonnement
        merchant_id = result["merchant_id"]

        try:
            # Vérifier si un abonnement existe déjà
            existing_sub = await self.subscription_repo.get_by_merchant(merchant_id)

            if existing_sub and existing_sub["status"] == "active":
                return {
                    "success": True,
                    "message": "Votre abonnement est déjà actif!"
                }

            if existing_sub:
                # Réactiver l'abonnement existant
                await self.subscription_repo.reactivate(merchant_id)
            else:
                # Créer un nouvel abonnement (essai gratuit pour commencer)
                await self.subscription_repo.create_trial(merchant_id)

            return {
                "success": True,
                "message": "Abonnement activé avec succès! Bienvenue sur KALGA."
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Erreur lors de l'activation: {str(e)}"
            }

    async def check_subscription_status(self, merchant_phone: str) -> dict:
        """
        Vérifie le statut d'abonnement d'un marchand.

        Returns:
            dict avec has_active_subscription, subscription_info
        """
        merchant = await self.merchant_repo.get_by_phone(merchant_phone)
        if not merchant and merchant_phone.startswith('225') and len(merchant_phone) == 12:
            merchant = await self.merchant_repo.get_by_phone('225' + '0' + merchant_phone[3:])
        if not merchant and merchant_phone.startswith('2250') and len(merchant_phone) == 13:
            merchant = await self.merchant_repo.get_by_phone('225' + merchant_phone[4:])
        if not merchant:
            return {
                "has_active_subscription": False,
                "reason": "merchant_not_found"
            }

        subscription = await self.subscription_repo.get_by_merchant(merchant["id"])

        if not subscription:
            return {
                "has_active_subscription": False,
                "reason": "no_subscription"
            }

        # Vérifier si l'abonnement est actif
        if subscription["status"] != "active":
            return {
                "has_active_subscription": False,
                "reason": "subscription_inactive",
                "status": subscription["status"]
            }

        # Vérifier si l'essai gratuit est expiré
        if subscription["plan"] == "trial" and subscription["trial_ends_at"]:
            trial_end = datetime.fromisoformat(subscription["trial_ends_at"])
            if datetime.now() > trial_end:
                return {
                    "has_active_subscription": False,
                    "reason": "trial_expired",
                    "expired_at": subscription["trial_ends_at"]
                }

        # Vérifier si l'abonnement payant est expiré
        if subscription["end_date"]:
            end_date = datetime.fromisoformat(subscription["end_date"])
            if datetime.now() > end_date:
                return {
                    "has_active_subscription": False,
                    "reason": "subscription_expired",
                    "expired_at": subscription["end_date"]
                }

        return {
            "has_active_subscription": True,
            "subscription": {
                "plan": subscription["plan"],
                "status": subscription["status"],
                "messages_used": subscription["messages_used"],
                "messages_limit": subscription["messages_limit"],
                "end_date": subscription.get("end_date"),
                "trial_ends_at": subscription.get("trial_ends_at")
            }
        }

    async def get_pending_activations(self) -> list:
        """Récupère la liste des marchands en attente d'activation"""
        return await self.activation_repo.get_pending_merchants()

    async def get_activation_history(self, limit: int = 50) -> list:
        """Récupère l'historique des activations"""
        return await self.activation_repo.get_activation_history(limit)


# Singleton
_activation_service: Optional[ActivationService] = None


def get_activation_service() -> ActivationService:
    """Factory pour le service d'activation"""
    global _activation_service
    if _activation_service is None:
        _activation_service = ActivationService()
    return _activation_service
