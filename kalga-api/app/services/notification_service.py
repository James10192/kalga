"""
Service de notification WhatsApp
Centralise tous les appels vers le bridge WhatsApp
"""
import httpx
import logging
from typing import Optional
from ..config import settings

logger = logging.getLogger("kalga.notifications")


class NotificationService:
    """
    Service pour envoyer des notifications via WhatsApp.
    Centralise les appels au bridge WhatsApp.
    """

    def __init__(self, bridge_url: str = None):
        self.bridge_url = bridge_url or settings.whatsapp_bridge_url
        self.timeout = 10.0

    async def send_message(
        self,
        merchant_phone: str,
        to: str,
        message: str
    ) -> bool:
        """
        Envoie un message texte via WhatsApp.

        Args:
            merchant_phone: Numéro du marchand (session WhatsApp)
            to: Numéro du destinataire
            message: Message à envoyer

        Returns:
            True si envoyé avec succès, False sinon
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.bridge_url}/send",
                    json={
                        "merchant_phone": merchant_phone,
                        "to": to,
                        "message": message
                    }
                )
                success = response.status_code == 200
                if success:
                    logger.info(f"Message envoyé à {to}")
                else:
                    logger.warning(f"Échec envoi message à {to}: {response.status_code}")
                return success
        except Exception as e:
            logger.error(f"Erreur envoi message: {e}")
            return False

    async def send_location(
        self,
        merchant_phone: str,
        to: str,
        latitude: float,
        longitude: float,
        name: str = "Ma boutique",
        address: str = ""
    ) -> bool:
        """
        Envoie une localisation GPS via WhatsApp.

        Args:
            merchant_phone: Numéro du marchand (session WhatsApp)
            to: Numéro du destinataire
            latitude: Latitude GPS
            longitude: Longitude GPS
            name: Nom du lieu
            address: Adresse textuelle

        Returns:
            True si envoyé avec succès, False sinon
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.bridge_url}/send-location",
                    json={
                        "merchant_phone": merchant_phone,
                        "to": to,
                        "latitude": latitude,
                        "longitude": longitude,
                        "name": name,
                        "address": address
                    }
                )
                success = response.status_code == 200
                if success:
                    logger.info(f"Localisation envoyée à {to}")
                else:
                    logger.warning(f"Échec envoi localisation à {to}: {response.status_code}")
                return success
        except Exception as e:
            logger.error(f"Erreur envoi localisation: {e}")
            return False

    async def send_image(
        self,
        merchant_phone: str,
        to: str,
        image_path: str,
        caption: str = ""
    ) -> bool:
        """
        Envoie une image via WhatsApp.

        Args:
            merchant_phone: Numéro du marchand (session WhatsApp)
            to: Numéro du destinataire
            image_path: Chemin de l'image sur le serveur
            caption: Légende de l'image

        Returns:
            True si envoyé avec succès, False sinon
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.bridge_url}/send-image",
                    json={
                        "merchant_phone": merchant_phone,
                        "to": to,
                        "image_path": image_path,
                        "caption": caption
                    }
                )
                success = response.status_code == 200
                if success:
                    logger.info(f"Image envoyée à {to}")
                else:
                    logger.warning(f"Échec envoi image à {to}: {response.status_code}")
                return success
        except Exception as e:
            logger.error(f"Erreur envoi image: {e}")
            return False

    # === Notifications métier prédéfinies ===

    async def notify_sale(
        self,
        merchant_phone: str,
        product_name: str,
        price: float,
        client_phone: str,
        product_code: str = "",
        delivery_type: str = "delivery",
        client_name: str = ""
    ) -> bool:
        """Notifie le marchand d'une vente confirmée"""
        if delivery_type == "pickup":
            type_label = "\U0001f3ea Récupération en boutique"
            action = "Le client va venir chercher le produit"
        else:
            type_label = "\U0001f69a Livraison"
            action = "Contacte le client pour organiser la livraison"

        code_str = f" ({product_code})" if product_code else ""

        # Afficher le nom du client si disponible, sinon juste indiquer de regarder la conversation
        client_info = ""
        if client_name:
            client_info = f"\U0001f464 *Client:* {client_name}\n"
        client_info += f"\U0001f4ac *Conversation:* Regarde tes messages recents pour trouver le client"

        message = (
            f"\U0001f514\U0001f514\U0001f514 *NOUVELLE VENTE!* \U0001f514\U0001f514\U0001f514\n\n"
            f"\U0001f4e6 *Produit:* {product_name}{code_str}\n"
            f"\U0001f4b0 *Prix accepté:* {price:,.0f} F\n"
            f"{client_info}\n"
            f"{type_label}\n\n"
            f"\U0001f449 {action}\n\n"
            f"_Tape *!ok* quand c'est livré ou *!annuler* pour annuler_"
        )
        return await self.send_message(merchant_phone, merchant_phone, message)

    async def notify_location_sent(
        self,
        merchant_phone: str,
        client_phone: str,
        product_name: str
    ) -> bool:
        """Notifie le marchand que la localisation a été envoyée au client"""
        message = f"📍 Localisation envoyée à {client_phone} pour {product_name}!"
        return await self.send_message(merchant_phone, merchant_phone, message)

    async def notify_location_needed(
        self,
        merchant_phone: str,
        client_phone: str,
        product_name: str
    ) -> bool:
        """Demande au marchand d'envoyer sa localisation"""
        message = f"📍 Client attend l'ADRESSE! {product_name} - Envoie ta localisation à {client_phone}"
        return await self.send_message(merchant_phone, merchant_phone, message)

    async def send_merchant_location_to_client(
        self,
        merchant_phone: str,
        client_phone: str,
        merchant_data: dict
    ) -> bool:
        """
        Envoie la localisation du marchand au client.

        Args:
            merchant_phone: Numéro du marchand
            client_phone: Numéro du client
            merchant_data: Données du marchand (latitude, longitude, address, etc.)

        Returns:
            True si envoyé avec succès, False sinon
        """
        latitude = merchant_data.get('latitude')
        longitude = merchant_data.get('longitude')
        address = merchant_data.get('address', '')

        logger.info(f"[LOCATION] send_merchant_location_to_client: lat={latitude}, lng={longitude}, addr={address}")

        if latitude and longitude:
            # Envoyer la localisation GPS
            name = merchant_data.get('business_name') or merchant_data.get('name') or 'Ma boutique'
            logger.info(f"[LOCATION] Envoi GPS: lat={latitude}, lng={longitude}, name={name}, to={client_phone}")
            result = await self.send_location(
                merchant_phone=merchant_phone,
                to=client_phone,
                latitude=latitude,
                longitude=longitude,
                name=name,
                address=address
            )
            logger.info(f"[LOCATION] Résultat envoi GPS: {result}")
            return result
        elif address:
            # Envoyer l'adresse en texte
            logger.info(f"[LOCATION] Pas de GPS, envoi adresse texte: {address}")
            message = f"📍 Voici l'adresse de la boutique:\n\n{address}"
            return await self.send_message(merchant_phone, client_phone, message)

        logger.warning(f"[LOCATION] Aucune donnée de localisation disponible pour {merchant_phone}")
        return False

    # === Notifications de Stock ===

    async def notify_low_stock(
        self,
        merchant_phone: str,
        product_name: str,
        product_code: str,
        remaining: int
    ) -> bool:
        """Alerte le marchand que le stock est bas"""
        message = (
            f"⚠️ *STOCK BAS*\n\n"
            f"📦 {product_name} ({product_code})\n"
            f"🔢 Plus que *{remaining}* en stock!\n\n"
            f"Pense à réapprovisionner."
        )
        return await self.send_message(merchant_phone, merchant_phone, message)

    async def notify_storefront_order(
        self,
        merchant_phone: str,
        client_name: str,
        client_phone: str,
        product_name: str,
        product_code: str,
        message: str = None
    ) -> bool:
        """Notifie le marchand d'une commande depuis la vitrine web"""
        msg = (
            f"\ud83d\uded2 *COMMANDE WEB*\n\n"
            f"\ud83d\udc64 Client: {client_name}\n"
            f"\ud83d\udcf1 Tel: {client_phone}\n"
            f"\ud83d\udce6 Produit: {product_name} ({product_code})\n"
        )
        if message:
            msg += f"\ud83d\udcac Message: {message}\n"
        msg += f"\n\ud83d\udcde Contacte ce client!"
        return await self.send_message(merchant_phone, merchant_phone, msg)

    def _get_storefront_url(self, merchant_phone: str) -> str:
        """Construit l'URL de la vitrine pour un marchand"""
        from ..config import settings
        return f"{settings.storefront_base_url}/boutique/boutique.html?m={merchant_phone}"

    async def send_storefront_welcome(
        self,
        merchant_phone: str,
        to: str,
        merchant_data: dict
    ) -> bool:
        """
        Envoie le lien de la vitrine au debut de la conversation (premier message).
        """
        store_name = merchant_data.get('business_name') or merchant_data.get('name') or 'notre boutique'
        storefront_url = self._get_storefront_url(merchant_phone)

        message = (
            f"\U0001f6cd\ufe0f Decouvre tous les produits de {store_name} ici :\n"
            f"\U0001f449 {storefront_url}"
        )
        return await self.send_message(merchant_phone, to, message)

    async def send_storefront_goodbye(
        self,
        merchant_phone: str,
        to: str,
        merchant_data: dict
    ) -> bool:
        """
        Envoie le lien de la vitrine a la fin d'une transaction reussie.
        N'envoie le lien que si STOREFRONT_BASE_URL est un vrai domaine public.
        """
        from ..config import settings

        store_name = merchant_data.get('business_name') or merchant_data.get('name') or 'notre boutique'

        # Si pas de vrai domaine, envoyer juste le remerciement sans lien
        if 'localhost' in settings.storefront_base_url or '127.0.0.1' in settings.storefront_base_url:
            message = (
                f"\U0001f64f Merci pour ton achat chez {store_name} !\n"
                f"N'hesite pas a revenir \U0001f60a"
            )
            return await self.send_message(merchant_phone, to, message)

        storefront_url = self._get_storefront_url(merchant_phone)

        message = (
            f"\U0001f64f Merci pour ton achat !\n"
            f"\U0001f6cd\ufe0f Visite notre boutique pour decouvrir d'autres produits :\n"
            f"\U0001f449 {storefront_url}"
        )
        return await self.send_message(merchant_phone, to, message)

    async def notify_out_of_stock(
        self,
        merchant_phone: str,
        product_name: str,
        product_code: str
    ) -> bool:
        """Alerte le marchand d'une rupture de stock"""
        message = (
            f"🚨 *RUPTURE DE STOCK*\n\n"
            f"📦 {product_name} ({product_code})\n"
            f"❌ Stock épuisé!\n\n"
            f"Le bot continuera à répondre mais informera les clients."
        )
        return await self.send_message(merchant_phone, merchant_phone, message)


# Instance globale
_notification_service: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    """Retourne l'instance globale du service de notification"""
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service
