"""
Repository pour la gestion des conversations et messages
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from .base import BaseRepository
from ..connection import get_connection


class ConversationRepository(BaseRepository):
    """Gère les opérations CRUD pour les conversations et messages"""

    def __init__(self):
        super().__init__("conversations")

    async def get_active(
        self,
        merchant_id: int,
        client_phone: str,
        product_id: int = None
    ) -> Optional[Dict[str, Any]]:
        """
        Récupère une conversation active entre un marchand et un client.
        Si product_id est fourni, cherche une conversation pour ce produit spécifique.
        """
        async with get_connection() as db:
            if product_id:
                cursor = await db.execute(
                    """
                    SELECT c.*, p.name as product_name, p.code as product_code, p.price
                    FROM conversations c
                    JOIN products p ON c.product_id = p.id
                    WHERE c.merchant_id = ?
                    AND c.client_phone = ?
                    AND c.product_id = ?
                    AND c.status NOT IN ('ended', 'completed', 'abandoned')
                    ORDER BY c.updated_at DESC
                    LIMIT 1
                    """,
                    (merchant_id, client_phone, product_id)
                )
            else:
                # Sans product_id = message sans code produit.
                # Exclure aussi pending_pickup/pending_delivery car ces conversations
                # sont "terminées" côté bot et ne doivent pas capturer de nouveaux messages.
                cursor = await db.execute(
                    """
                    SELECT c.*, p.name as product_name, p.code as product_code, p.price
                    FROM conversations c
                    JOIN products p ON c.product_id = p.id
                    WHERE c.merchant_id = ?
                    AND c.client_phone = ?
                    AND c.status NOT IN ('ended', 'completed', 'abandoned', 'pending_pickup', 'pending_delivery')
                    ORDER BY c.updated_at DESC
                    LIMIT 1
                    """,
                    (merchant_id, client_phone)
                )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def create(
        self,
        merchant_id: int,
        product_id: int,
        client_phone: str
    ) -> Dict[str, Any]:
        """Crée une nouvelle conversation"""
        async with get_connection() as db:
            cursor = await db.execute(
                """
                INSERT INTO conversations (merchant_id, product_id, client_phone, status)
                VALUES (?, ?, ?, 'active')
                """,
                (merchant_id, product_id, client_phone)
            )
            await db.commit()
            conv_id = cursor.lastrowid

            # Récupérer la conversation créée avec les infos produit
            cursor = await db.execute(
                """
                SELECT c.*, p.name as product_name, p.code as product_code, p.price
                FROM conversations c
                JOIN products p ON c.product_id = p.id
                WHERE c.id = ?
                """,
                (conv_id,)
            )
            row = await cursor.fetchone()
            return dict(row)

    async def update(self, conversation_id: int, **kwargs) -> bool:
        """Met à jour une conversation avec les champs fournis"""
        if not kwargs:
            return False

        # Toujours mettre à jour updated_at
        kwargs['updated_at'] = datetime.now().isoformat()

        fields = ", ".join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values())
        values.append(conversation_id)

        async with get_connection() as db:
            cursor = await db.execute(
                f"UPDATE conversations SET {fields} WHERE id = ?",
                tuple(values)
            )
            await db.commit()
            return cursor.rowcount > 0

    async def get_by_merchant(
        self,
        merchant_id: int,
        status: str = "active"
    ) -> List[Dict[str, Any]]:
        """Récupère les conversations d'un marchand par statut"""
        async with get_connection() as db:
            if status == "all":
                cursor = await db.execute(
                    """
                    SELECT c.*, p.name as product_name, p.code as product_code, p.price
                    FROM conversations c
                    JOIN products p ON c.product_id = p.id
                    WHERE c.merchant_id = ?
                    ORDER BY c.updated_at DESC
                    """,
                    (merchant_id,)
                )
            elif status == "active":
                cursor = await db.execute(
                    """
                    SELECT c.*, p.name as product_name, p.code as product_code, p.price
                    FROM conversations c
                    JOIN products p ON c.product_id = p.id
                    WHERE c.merchant_id = ?
                    AND c.status NOT IN ('ended', 'completed', 'abandoned')
                    ORDER BY c.updated_at DESC
                    """,
                    (merchant_id,)
                )
            else:
                cursor = await db.execute(
                    """
                    SELECT c.*, p.name as product_name, p.code as product_code, p.price
                    FROM conversations c
                    JOIN products p ON c.product_id = p.id
                    WHERE c.merchant_id = ? AND c.status = ?
                    ORDER BY c.updated_at DESC
                    """,
                    (merchant_id, status)
                )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_pending(self, merchant_id: int) -> List[Dict[str, Any]]:
        """Récupère les conversations en attente (pending_delivery ou pending_pickup)"""
        async with get_connection() as db:
            cursor = await db.execute(
                """
                SELECT c.*, p.name as product_name, p.code as product_code, p.price
                FROM conversations c
                JOIN products p ON c.product_id = p.id
                WHERE c.merchant_id = ?
                AND c.status IN ('pending_delivery', 'pending_pickup')
                ORDER BY c.updated_at DESC
                """,
                (merchant_id,)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    # === Gestion des messages ===

    async def add_message(
        self,
        conversation_id: int,
        content: str,
        is_from_client: bool
    ) -> Dict[str, Any]:
        """Ajoute un message à une conversation"""
        async with get_connection() as db:
            cursor = await db.execute(
                """
                INSERT INTO messages (conversation_id, content, is_from_client)
                VALUES (?, ?, ?)
                """,
                (conversation_id, content, is_from_client)
            )

            # Mettre à jour updated_at de la conversation
            await db.execute(
                "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (conversation_id,)
            )
            await db.commit()
            message_id = cursor.lastrowid

            cursor = await db.execute(
                "SELECT * FROM messages WHERE id = ?",
                (message_id,)
            )
            row = await cursor.fetchone()
            return dict(row)

    async def get_messages(self, conversation_id: int) -> List[Dict[str, Any]]:
        """Récupère tous les messages d'une conversation"""
        async with get_connection() as db:
            cursor = await db.execute(
                """
                SELECT * FROM messages
                WHERE conversation_id = ?
                ORDER BY created_at ASC
                """,
                (conversation_id,)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    # === Nettoyage ===

    async def cleanup_expired(self, days: int = 7) -> int:
        """Marque les conversations inactives depuis X jours comme terminées"""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        async with get_connection() as db:
            cursor = await db.execute(
                """
                UPDATE conversations
                SET status = 'expired'
                WHERE status IN ('active', 'negotiating')
                AND updated_at < ?
                """,
                (cutoff,)
            )
            await db.commit()
            return cursor.rowcount


# Instance globale
_conversation_repo: Optional['ConversationRepository'] = None


def get_conversation_repository() -> 'ConversationRepository':
    """Retourne l'instance globale du repository"""
    global _conversation_repo
    if _conversation_repo is None:
        _conversation_repo = ConversationRepository()
    return _conversation_repo
