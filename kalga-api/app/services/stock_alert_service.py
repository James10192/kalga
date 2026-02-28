"""
Service d'alertes stock automatiques
Scheduler proactif : alertes stock bas + dialogue marchand + broadcast waitlist

Architecture: miroir de FollowUpService (asyncio.create_task + scheduler loop)
"""
import asyncio
import logging
from typing import Optional
from datetime import datetime

from ..database.connection import get_connection
from ..database.repositories.waitlist_repo import get_waitlist_repository
from .notification_service import get_notification_service

logger = logging.getLogger("kalga.stock_alert")


class StockAlertService:
    """
    Deux responsabilités :
    1. Scheduler (toutes les 5 min) : alertes proactives marchand pour produits épuisés
    2. Trigger ponctuel : broadcast waitlist quand stock renouvelé
    """

    def __init__(self):
        self.notifications = get_notification_service()
        self.waitlist = get_waitlist_repository()
        self._task: Optional[asyncio.Task] = None
        self._running = False

    async def start_scheduler(self, interval_seconds: int = 300):
        """Démarre le scheduler en arrière-plan (toutes les 5 minutes)"""
        self._running = True
        self._task = asyncio.create_task(
            self._scheduler_loop(interval_seconds),
            name="stock_alert_scheduler"
        )
        logger.info(f"[StockAlert] Scheduler démarré (interval={interval_seconds}s)")

    def stop_scheduler(self):
        self._running = False
        if self._task:
            self._task.cancel()
        logger.info("[StockAlert] Scheduler arrêté")

    async def _scheduler_loop(self, interval_seconds: int):
        """Boucle principale du scheduler"""
        while self._running:
            try:
                await self._process_proactive_alerts()
            except Exception as e:
                logger.error(f"[StockAlert] Erreur scheduler: {e}")
            await asyncio.sleep(interval_seconds)

    async def _process_proactive_alerts(self):
        """
        Pour chaque marchand avec alertes activées :
        - Récupère les produits épuisés depuis X jours
        - Envoie le dialogue proactif (3 options) si pas encore fait aujourd'hui
        """
        try:
            async with get_connection() as db:
                cursor = await db.execute(
                    """SELECT id, phone, name, stock_alert_days, stock_alerts_enabled
                       FROM merchants
                       WHERE stock_alerts_enabled = 1 OR stock_alerts_enabled IS NULL"""
                )
                merchants = [dict(r) for r in await cursor.fetchall()]

            for merchant in merchants:
                try:
                    alert_days = merchant.get('stock_alert_days') or 3
                    products = await self.waitlist.get_products_out_of_stock_since(
                        merchant['id'], days=alert_days
                    )
                    for product in products:
                        await self._send_merchant_stock_dialogue(
                            merchant=merchant,
                            product=product
                        )
                        # Marquer last_stock_alert_at pour éviter le spam
                        async with get_connection() as db:
                            await db.execute(
                                "UPDATE products SET last_stock_alert_at = CURRENT_TIMESTAMP WHERE id = ?",
                                (product['id'],)
                            )
                            await db.commit()
                        await asyncio.sleep(1)  # Rate-limit entre marchands
                except Exception as e:
                    logger.warning(f"[StockAlert] Erreur traitement marchand {merchant['id']}: {e}")

        except Exception as e:
            logger.error(f"[StockAlert] Erreur process_proactive_alerts: {e}")

    async def _send_merchant_stock_dialogue(
        self,
        merchant: dict,
        product: dict
    ):
        """Envoie le dialogue proactif 3 options au marchand"""
        merchant_phone = merchant['phone']
        first_name = (merchant.get('name') or 'Marchand').split()[0]
        waitlist_count = product.get('waitlist_count', 0)
        out_since = product.get('out_since', '')

        # Calculer le nombre de jours depuis rupture
        days_text = ""
        if out_since:
            try:
                out_dt = datetime.fromisoformat(out_since.replace('Z', ''))
                days_elapsed = (datetime.now() - out_dt).days
                days_text = f"{days_elapsed} jour{'s' if days_elapsed > 1 else ''}"
            except Exception:
                days_text = "quelques jours"

        waitlist_text = (
            f"\n👥 *{waitlist_count} client{'s' if waitlist_count > 1 else ''} attend{'ent' if waitlist_count > 1 else ''}* une notification."
            if waitlist_count > 0 else ""
        )

        message = (
            f"👋 Bonjour {first_name} !\n\n"
            f"📦 *{product['name']}* ({product['code']}) est épuisé"
            f"{' depuis ' + days_text if days_text else ''}."
            f"{waitlist_text}\n\n"
            f"Le stock a été renouvelé ?\n\n"
            f"1️⃣ *Oui* — mettre à jour le stock\n"
            f"2️⃣ *Non* — pas encore\n"
            f"3️⃣ *Supprimer* cet article"
        )
        await self.notifications.send_message(
            merchant_phone=merchant_phone,
            to=merchant_phone,
            message=message
        )
        # Enregistrer la session pour capturer la réponse du marchand
        try:
            from ..modules.merchant_commands.service import register_stock_dialogue_session
            register_stock_dialogue_session(
                merchant_phone=merchant_phone,
                product_id=product['id'],
                product_code=product['code'],
                product_name=product['name']
            )
        except Exception as e:
            logger.warning(f"[StockAlert] register_stock_session: {e}")
        logger.info(f"[StockAlert] Dialogue proactif envoyé: {merchant_phone} → {product['code']}")

    async def broadcast_waitlist_on_restock(
        self,
        merchant_id: int,
        merchant_phone: str,
        product_id: int,
        product_name: str,
        product_code: str,
        new_quantity: int,
        store_name: str = ""
    ) -> int:
        """
        Notifie les clients en waitlist quand le stock est renouvelé.
        Retourne le nombre de clients notifiés.
        FIFO : notifie au maximum new_quantity clients.
        """
        waitlist = await self.waitlist.get_waitlist_for_product(product_id, status='waiting')
        if not waitlist:
            return 0

        # Limiter aux clients qu'on peut réellement servir (FIFO)
        to_notify = waitlist[:max(new_quantity, 1)] if new_quantity > 0 else waitlist
        notified_ids = []
        count = 0

        store_label = store_name or "notre boutique"

        for entry in to_notify:
            client_phone = entry['client_phone']
            message = (
                f"🎉 Bonne nouvelle !\n\n"
                f"*{product_name}* ({product_code}) est à nouveau disponible "
                f"chez *{store_label}* !\n\n"
                f"Réponds avec le code *{product_code}* pour commander maintenant 👇"
            )
            success = await self.notifications.send_message(
                merchant_phone=merchant_phone,
                to=client_phone,
                message=message
            )
            if success:
                notified_ids.append(entry['id'])
                count += 1
            await asyncio.sleep(0.5)  # Évite le flood WhatsApp

        if notified_ids:
            await self.waitlist.mark_notified(notified_ids)

        logger.info(
            f"[StockAlert] Broadcast restock {product_code}: "
            f"{count}/{len(waitlist)} clients notifiés"
        )
        return count


# Instance globale
_stock_alert_service: Optional[StockAlertService] = None


def get_stock_alert_service() -> StockAlertService:
    global _stock_alert_service
    if _stock_alert_service is None:
        _stock_alert_service = StockAlertService()
    return _stock_alert_service
