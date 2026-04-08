"""
Client HTTP pour communiquer avec le WhatsApp Bridge
"""
import httpx
import logging
from typing import Optional

from ...core.config import settings
from ...core.exceptions import WhatsAppBridgeError

logger = logging.getLogger("kalga.whatsapp")


class WhatsAppBridgeClient:
    """Client pour le service WhatsApp Bridge"""

    def __init__(self):
        self.base_url = settings.whatsapp_bridge_url
        self.timeout = settings.whatsapp_request_timeout

    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> dict:
        """Effectue une requête HTTP vers le bridge"""
        url = f"{self.base_url}{endpoint}"

        try:
            headers = kwargs.pop("headers", {})
            if settings.internal_api_key:
                headers["X-Internal-Key"] = settings.internal_api_key
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method,
                    url,
                    timeout=self.timeout,
                    headers=headers,
                    **kwargs
                )
                response.raise_for_status()
                return response.json()

        except httpx.TimeoutException:
            raise WhatsAppBridgeError(f"Timeout lors de l'appel à {endpoint}")
        except httpx.HTTPStatusError as e:
            raise WhatsAppBridgeError(f"Erreur HTTP {e.response.status_code}: {endpoint}")
        except Exception as e:
            raise WhatsAppBridgeError(str(e))

    async def send_message(
        self,
        merchant_phone: str,
        to: str,
        message: str
    ) -> bool:
        """Envoie un message texte"""
        try:
            result = await self._request(
                "POST",
                "/send",
                json={
                    "merchant_phone": merchant_phone,
                    "to": to,
                    "message": message
                }
            )
            return result.get("success", False)
        except WhatsAppBridgeError as e:
            logger.error(f"Erreur envoi message: {e}")
            return False

    async def send_image(
        self,
        merchant_phone: str,
        to: str,
        image_path: str,
        caption: str = ""
    ) -> bool:
        """Envoie une image"""
        try:
            result = await self._request(
                "POST",
                "/send-image",
                json={
                    "merchant_phone": merchant_phone,
                    "to": to,
                    "image_path": image_path,
                    "caption": caption
                }
            )
            return result.get("success", False)
        except WhatsAppBridgeError as e:
            logger.error(f"Erreur envoi image: {e}")
            return False

    async def send_location(
        self,
        merchant_phone: str,
        to: str,
        latitude: float,
        longitude: float,
        name: str = "",
        address: str = ""
    ) -> bool:
        """Envoie une localisation GPS"""
        try:
            result = await self._request(
                "POST",
                "/send-location",
                json={
                    "merchant_phone": merchant_phone,
                    "to": to,
                    "latitude": latitude,
                    "longitude": longitude,
                    "name": name,
                    "address": address
                }
            )
            return result.get("success", False)
        except WhatsAppBridgeError as e:
            logger.error(f"Erreur envoi localisation: {e}")
            return False

    async def get_status(self, merchant_phone: str) -> Optional[dict]:
        """Récupère le statut d'un marchand"""
        try:
            return await self._request("GET", f"/status/{merchant_phone}")
        except WhatsAppBridgeError:
            return None

    async def health_check(self) -> bool:
        """Vérifie si le bridge est accessible"""
        try:
            result = await self._request("GET", "/health")
            return result.get("status") == "ok"
        except WhatsAppBridgeError:
            return False


# Instance singleton
whatsapp_client = WhatsAppBridgeClient()
