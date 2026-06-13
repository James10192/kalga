"""
Couche de compatibilité pour l'accès à la base de données.
Ce fichier délègue aux repositories tout en gardant l'API existante
pour ne pas casser le code existant.

Usage recommandé (nouveau code):
    from app.database.repositories import MerchantRepository
    merchant_repo = MerchantRepository()
    merchant = await merchant_repo.get_by_phone("225XXXXXXXX")

Usage legacy (ancien code - toujours supporté):
    from app.database import get_db
    db = await get_db()
    merchant = await db.get_merchant_by_phone("225XXXXXXXX")
"""
from typing import Optional, List, Dict, Any

from .repositories import MerchantRepository, ProductRepository, ConversationRepository


class Database:
    """
    Classe de compatibilité qui délègue aux repositories (tous back-Convex
    depuis le plan 004). Garde la même interface que l'ancien code.

    Phase F : plus aucune dépendance SQLite. `init()` est un no-op conservé pour
    rétrocompatibilité (le schéma vit dans Convex, plus de bootstrap local).
    """

    def __init__(self):
        self.merchants = MerchantRepository()
        self.products = ProductRepository()
        self.conversations = ConversationRepository()

    async def init(self):
        """No-op (Convex est la source de vérité — plus de schéma SQLite local)."""
        return None

    # === MARCHANDS (délègue à MerchantRepository) ===

    async def create_merchant(self, name: str, phone: str, business_name: str = None) -> Dict:
        return await self.merchants.create(name, phone, business_name)

    async def get_merchant_by_phone(self, phone: str) -> Optional[Dict]:
        return await self.merchants.get_by_phone(phone)

    async def get_all_merchants(self) -> List[Dict]:
        return await self.merchants.get_all(page=1, limit=1000)

    async def update_merchant_location(
        self,
        merchant_id: int,
        address: str = None,
        latitude: float = None,
        longitude: float = None
    ) -> bool:
        return await self.merchants.update_location(merchant_id, address, latitude, longitude)

    async def update_merchant(self, merchant_id: int, **kwargs) -> bool:
        return await self.merchants.update(merchant_id, **kwargs)

    # === PRODUITS (délègue à ProductRepository) ===

    async def create_product(
        self,
        merchant_id: int,
        name: str,
        price: float,
        min_price: float,
        description: str = None,
        image_path: str = None,
        group_id: str = None,
        variant_name: str = None
    ) -> Dict:
        return await self.products.create(
            merchant_id=merchant_id,
            name=name,
            price=price,
            min_price=min_price,
            description=description,
            image_path=image_path,
            group_id=group_id,
            variant_name=variant_name
        )

    async def get_product_by_code(self, code: str) -> Optional[Dict]:
        product = await self.products.get_by_code(code)
        if product:
            # Ajouter les infos du marchand pour la compatibilité
            merchant = await self.merchants.get_by_id(product['merchant_id'])
            if merchant:
                product['merchant_phone'] = merchant.get('phone')
                product['merchant_name'] = merchant.get('name')
        return product

    async def get_products_by_merchant(self, merchant_id: int) -> List[Dict]:
        return await self.products.get_by_merchant(merchant_id)

    async def get_product_by_id(self, product_id: int) -> Optional[Dict]:
        product = await self.products.get_by_id(product_id)
        if product:
            # Ajouter les infos du marchand pour la compatibilité
            merchant = await self.merchants.get_by_id(product['merchant_id'])
            if merchant:
                product['merchant_phone'] = merchant.get('phone')
                product['merchant_name'] = merchant.get('name')
        return product

    async def update_product(self, product_id: int, **kwargs) -> bool:
        """Met à jour un produit avec les champs fournis"""
        return await self.products.update(product_id, **kwargs)

    async def deactivate_product(self, code: str):
        product = await self.products.get_by_code(code)
        if product:
            await self.products.deactivate(product['id'])

    async def get_product_variants(self, group_id: str) -> List[Dict]:
        """Toutes les variantes d'un groupe (délègue à Convex via ProductRepository)."""
        return await self.products.get_all_in_group(group_id)

    async def get_other_variants(self, product_id: int, group_id: str) -> List[Dict]:
        return await self.products.get_other_variants(product_id, group_id)

    async def generate_group_id(self) -> str:
        import uuid
        return f"GRP-{uuid.uuid4().hex[:8].upper()}"

    # === CONVERSATIONS (délègue à ConversationRepository) ===

    async def create_conversation(self, merchant_id: int, product_id: int, client_phone: str) -> Dict:
        return await self.conversations.create(merchant_id, product_id, client_phone)

    async def get_active_conversation(
        self,
        merchant_id: int,
        client_phone: str,
        product_id: int = None
    ) -> Optional[Dict]:
        return await self.conversations.get_active(merchant_id, client_phone, product_id)

    async def update_conversation(self, conversation_id: int, status: str = None, current_offer: float = None):
        kwargs = {}
        if status is not None:
            kwargs['status'] = status
        if current_offer is not None:
            kwargs['current_offer'] = current_offer
        await self.conversations.update(conversation_id, **kwargs)

    async def cleanup_expired_conversations(self, days: int = 7):
        return await self.conversations.cleanup_expired(days)

    async def get_conversations_by_merchant(self, merchant_id: int, status: str = "active") -> List[Dict]:
        return await self.conversations.get_by_merchant(merchant_id, status)

    async def get_conversation_by_id(self, conversation_id: int) -> Optional[Dict]:
        return await self.conversations.get_by_id(conversation_id)

    async def get_pending_conversations(self, merchant_id: int) -> List[Dict]:
        return await self.conversations.get_pending(merchant_id)

    # === MESSAGES (délègue à ConversationRepository) ===

    async def add_message(self, conversation_id: int, content: str, is_from_client: bool) -> Dict:
        return await self.conversations.add_message(conversation_id, content, is_from_client)

    async def get_conversation_messages(self, conversation_id: int, limit: int = 20) -> List[Dict]:
        messages = await self.conversations.get_messages(conversation_id)
        # Limiter et retourner dans l'ordre chronologique
        return messages[-limit:] if len(messages) > limit else messages


# Instance globale pour la rétrocompatibilité
_db: Optional[Database] = None


async def get_db() -> Database:
    """
    Retourne l'instance globale de la base de données.
    Initialise la DB au premier appel.
    """
    global _db
    if _db is None:
        _db = Database()
        await _db.init()
    return _db
