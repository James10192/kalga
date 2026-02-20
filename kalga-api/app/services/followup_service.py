"""
Service de relances automatiques
Gère la planification et l'envoi de messages de suivi aux clients
"""
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import random

from ..database.connection import get_connection
from .notification_service import get_notification_service

logger = logging.getLogger("kalga.followup")


class FollowUpService:
    """
    Service pour gérer les relances automatiques.
    Planifie et envoie des messages de suivi aux clients inactifs.
    """

    # Messages de relance par étape
    FOLLOW_UP_MESSAGES = {
        1: [  # Première relance (après 2h)
            "Hey! Tu as vu le {product}? Il te plaît?",
            "Salut! Tu réfléchis encore pour le {product}?",
            "Coucou! Des questions sur le {product}?",
            "Hello! Le {product} est toujours dispo si ça t'intéresse!",
        ],
        2: [  # Deuxième relance (après 24h)
            "Juste pour te dire, le {product} part vite! Tu veux qu'on en parle?",
            "Hello! Je peux te faire un prix spécial sur le {product} si tu te décides aujourd'hui!",
            "Salut! Le {product} est encore disponible mais j'ai d'autres clients intéressés...",
        ],
        3: [  # Dernière relance (après 48h)
            "Dernière chance pour le {product}! Après je ne pourrai plus garantir le prix.",
            "C'est ma dernière relance pour le {product}. Fais-moi signe si t'es toujours intéressé!",
        ]
    }

    # Délais de relance (en heures)
    FOLLOW_UP_DELAYS = {
        1: 2,    # 2 heures après dernier message
        2: 24,   # 24 heures
        3: 48,   # 48 heures
    }

    def __init__(self):
        self.notifications = get_notification_service()
        self._running = False
        self._task = None

    async def schedule_follow_up(
        self,
        conversation_id: int,
        merchant_id: int,
        merchant_phone: str,
        client_phone: str,
        product_name: str,
        step: int = 1
    ) -> Optional[int]:
        """
        Planifie une relance pour une conversation.

        Args:
            conversation_id: ID de la conversation
            merchant_id: ID du marchand
            merchant_phone: Numéro WhatsApp du marchand
            client_phone: Numéro du client
            product_name: Nom du produit
            step: Étape de la relance (1, 2, ou 3)

        Returns:
            ID de la relance créée ou None
        """
        if step > 3:
            logger.info(f"Pas de relance step {step} pour conversation {conversation_id}")
            return None

        delay_hours = self.FOLLOW_UP_DELAYS.get(step, 2)
        scheduled_at = datetime.now() + timedelta(hours=delay_hours)

        # Choisir un message aléatoire
        messages = self.FOLLOW_UP_MESSAGES.get(step, self.FOLLOW_UP_MESSAGES[1])
        message = random.choice(messages).format(product=product_name)

        async with get_connection() as db:
            # Vérifier qu'il n'y a pas déjà une relance en attente
            cursor = await db.execute(
                """
                SELECT id FROM follow_ups
                WHERE conversation_id = ? AND status = 'pending'
                """,
                (conversation_id,)
            )
            existing = await cursor.fetchone()
            if existing:
                logger.debug(f"Relance déjà planifiée pour conversation {conversation_id}")
                return None

            # Créer la relance
            cursor = await db.execute(
                """
                INSERT INTO follow_ups
                (conversation_id, merchant_id, client_phone, scheduled_at, message, status)
                VALUES (?, ?, ?, ?, ?, 'pending')
                """,
                (conversation_id, merchant_id, client_phone, scheduled_at.isoformat(), message)
            )
            await db.commit()

            followup_id = cursor.lastrowid
            logger.info(f"Relance #{followup_id} planifiée pour {scheduled_at}")
            return followup_id

    async def cancel_follow_ups(self, conversation_id: int) -> int:
        """
        Annule toutes les relances en attente pour une conversation.
        Appelé quand le client répond ou quand la conversation est terminée.

        Returns:
            Nombre de relances annulées
        """
        async with get_connection() as db:
            cursor = await db.execute(
                """
                UPDATE follow_ups
                SET status = 'cancelled'
                WHERE conversation_id = ? AND status = 'pending'
                """,
                (conversation_id,)
            )
            await db.commit()

            if cursor.rowcount > 0:
                logger.info(f"Annulé {cursor.rowcount} relances pour conversation {conversation_id}")

            return cursor.rowcount

    async def get_pending_follow_ups(self) -> List[Dict[str, Any]]:
        """Récupère les relances à envoyer maintenant"""
        now = datetime.now().isoformat()

        async with get_connection() as db:
            cursor = await db.execute(
                """
                SELECT f.*, m.phone as merchant_phone, c.product_id, p.name as product_name
                FROM follow_ups f
                JOIN merchants m ON f.merchant_id = m.id
                JOIN conversations c ON f.conversation_id = c.id
                JOIN products p ON c.product_id = p.id
                WHERE f.status = 'pending' AND f.scheduled_at <= ?
                ORDER BY f.scheduled_at ASC
                LIMIT 50
                """,
                (now,)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def send_follow_up(self, followup: Dict[str, Any]) -> bool:
        """
        Envoie une relance et met à jour son statut.

        Returns:
            True si envoyé avec succès
        """
        try:
            # Vérifier que la conversation est toujours active/négociation
            async with get_connection() as db:
                cursor = await db.execute(
                    "SELECT status FROM conversations WHERE id = ?",
                    (followup['conversation_id'],)
                )
                conv = await cursor.fetchone()

                if not conv or conv[0] not in ('active', 'negotiating', 'agreed'):
                    # Conversation terminée, annuler la relance
                    await db.execute(
                        "UPDATE follow_ups SET status = 'cancelled' WHERE id = ?",
                        (followup['id'],)
                    )
                    await db.commit()
                    logger.info(f"Relance #{followup['id']} annulée (conversation {conv[0] if conv else 'inexistante'})")
                    return False

            # Envoyer le message
            success = await self.notifications.send_message(
                merchant_phone=followup['merchant_phone'],
                to=followup['client_phone'],
                message=followup['message']
            )

            # Mettre à jour le statut
            async with get_connection() as db:
                if success:
                    await db.execute(
                        """
                        UPDATE follow_ups
                        SET status = 'sent', sent_at = ?
                        WHERE id = ?
                        """,
                        (datetime.now().isoformat(), followup['id'])
                    )
                    logger.info(f"Relance #{followup['id']} envoyée à {followup['client_phone']}")

                    # Enregistrer le message dans la conversation
                    await db.execute(
                        """
                        INSERT INTO messages (conversation_id, content, is_from_client)
                        VALUES (?, ?, 0)
                        """,
                        (followup['conversation_id'], followup['message'])
                    )

                    # Planifier la prochaine relance
                    step = await self._get_current_step(followup['conversation_id'])
                    if step < 3:
                        await self.schedule_follow_up(
                            conversation_id=followup['conversation_id'],
                            merchant_id=followup['merchant_id'],
                            merchant_phone=followup['merchant_phone'],
                            client_phone=followup['client_phone'],
                            product_name=followup['product_name'],
                            step=step + 1
                        )
                else:
                    await db.execute(
                        "UPDATE follow_ups SET status = 'failed' WHERE id = ?",
                        (followup['id'],)
                    )
                    logger.warning(f"Échec envoi relance #{followup['id']}")

                await db.commit()

            return success

        except Exception as e:
            logger.error(f"Erreur envoi relance #{followup['id']}: {e}")
            return False

    async def _get_current_step(self, conversation_id: int) -> int:
        """Compte le nombre de relances déjà envoyées pour une conversation"""
        async with get_connection() as db:
            cursor = await db.execute(
                """
                SELECT COUNT(*) FROM follow_ups
                WHERE conversation_id = ? AND status = 'sent'
                """,
                (conversation_id,)
            )
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def process_pending_follow_ups(self) -> int:
        """
        Traite toutes les relances en attente.
        Retourne le nombre de relances envoyées.
        """
        pending = await self.get_pending_follow_ups()
        sent_count = 0

        for followup in pending:
            if await self.send_follow_up(followup):
                sent_count += 1
            # Petite pause entre les envois pour éviter le spam
            await asyncio.sleep(1)

        return sent_count

    async def start_scheduler(self, interval_seconds: int = 60):
        """
        Démarre le scheduler de relances en arrière-plan.
        Vérifie les relances à envoyer toutes les X secondes.
        """
        if self._running:
            logger.warning("Scheduler déjà en cours d'exécution")
            return

        self._running = True
        logger.info(f"Démarrage du scheduler de relances (intervalle: {interval_seconds}s)")

        async def _scheduler_loop():
            while self._running:
                try:
                    sent = await self.process_pending_follow_ups()
                    if sent > 0:
                        logger.info(f"Scheduler: {sent} relances envoyées")
                except Exception as e:
                    logger.error(f"Erreur scheduler: {e}")

                await asyncio.sleep(interval_seconds)

        self._task = asyncio.create_task(_scheduler_loop())

    def stop_scheduler(self):
        """Arrête le scheduler"""
        self._running = False
        if self._task:
            self._task.cancel()
            logger.info("Scheduler de relances arrêté")


# Instance globale
_followup_service: Optional[FollowUpService] = None


def get_followup_service() -> FollowUpService:
    """Retourne l'instance globale du service de relances"""
    global _followup_service
    if _followup_service is None:
        _followup_service = FollowUpService()
    return _followup_service
