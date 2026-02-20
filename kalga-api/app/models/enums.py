"""
Énumérations pour KALGA
Définit les constantes et états du système
"""
from enum import Enum


class ConversationStatus(str, Enum):
    """États possibles d'une conversation"""
    ACTIVE = "active"                    # Conversation en cours
    NEGOTIATING = "negotiating"          # Négociation de prix en cours
    AGREED = "agreed"                    # Prix accepté, en attente du choix livraison/pickup
    PENDING_DELIVERY = "pending_delivery"  # En attente de livraison
    PENDING_PICKUP = "pending_pickup"    # En attente de récupération au magasin
    COMPLETED = "completed"              # Vente terminée
    ABANDONED = "abandoned"              # Client a abandonné
    ENDED = "ended"                      # Conversation terminée (sans vente)
    EXPIRED = "expired"                  # Conversation expirée (7+ jours)


class MessageType(str, Enum):
    """Types de messages"""
    TEXT = "text"
    IMAGE = "image"
    LOCATION = "location"
    VOICE = "voice"


class NotificationType(str, Enum):
    """Types de notifications"""
    SALE = "sale"
    LOCATION_SENT = "location_sent"
    LOCATION_NEEDED = "location_needed"
    SALE_COMPLETED = "sale_completed"
    SALE_CANCELLED = "sale_cancelled"
