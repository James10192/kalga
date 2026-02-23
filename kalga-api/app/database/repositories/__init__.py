"""
Repositories - Couche d'accès aux données
Chaque repository gère les opérations CRUD pour un domaine métier spécifique.
"""
from .merchant_repo import MerchantRepository, get_merchant_repository
from .product_repo import ProductRepository
from .conversation_repo import ConversationRepository, get_conversation_repository
from .stats_repo import StatsRepository, get_stats_repository
from .user_repo import UserRepository, get_user_repository
from .subscription_repo import SubscriptionRepository, get_subscription_repository
from .client_history_repo import ClientHistoryRepository, get_client_history_repository
from .activation_repo import ActivationRepository, get_activation_repository
from .storefront_order_repo import StorefrontOrderRepository, get_storefront_order_repository
from .knowledge_repo import KnowledgeBaseRepository, extract_keywords

__all__ = [
    "MerchantRepository",
    "get_merchant_repository",
    "ProductRepository",
    "ConversationRepository",
    "get_conversation_repository",
    "StatsRepository",
    "get_stats_repository",
    "UserRepository",
    "get_user_repository",
    "SubscriptionRepository",
    "get_subscription_repository",
    "ClientHistoryRepository",
    "get_client_history_repository",
    "ActivationRepository",
    "get_activation_repository",
    "StorefrontOrderRepository",
    "get_storefront_order_repository",
    "KnowledgeBaseRepository",
    "extract_keywords",
]
