from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
from enum import Enum
import re


# === VALIDATION TELEPHONE ===
def validate_phone_number(phone: str) -> str:
    """
    Valide et normalise un numéro de téléphone international.
    Formats acceptés:
    - Numéro complet avec indicatif (ex: 225XXXXXXXXX, 33XXXXXXXXX)
    - +INDICATIF suivi du numéro
    Le numéro doit avoir entre 10 et 15 chiffres au total.
    """
    # Nettoyer: enlever espaces, tirets, +, parenthèses
    clean = re.sub(r'[\s\-\+\(\)]', '', phone)

    # Vérifier que c'est uniquement des chiffres
    if not clean.isdigit():
        raise ValueError(f'Le numéro ne doit contenir que des chiffres: {phone}')

    # Vérifier la longueur (10 à 15 chiffres avec indicatif)
    if len(clean) < 10 or len(clean) > 15:
        raise ValueError(
            f'Numéro invalide: {phone}. '
            'Le numéro doit avoir entre 10 et 15 chiffres (indicatif inclus).'
        )

    return clean


class ConversationStatus(str, Enum):
    ACTIVE = "active"           # Conversation en cours
    COMPLETED = "completed"     # Vente conclue
    ABANDONED = "abandoned"     # Client parti
    EXPIRED = "expired"         # 7 jours dépassés


# === MARCHAND ===
class MerchantCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    phone: str                  # Numéro WhatsApp du marchand
    business_name: Optional[str] = Field(None, max_length=200)

    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v):
        return validate_phone_number(v)


class Merchant(MerchantCreate):
    id: int
    created_at: datetime
    is_active: bool = True

    class Config:
        from_attributes = True


# === PRODUIT ===
class ProductCreate(BaseModel):
    merchant_id: int
    name: str
    description: Optional[str] = None
    price: float                # Prix normal
    min_price: float            # Prix minimum négociable
    image_path: Optional[str] = None      # Chemin vers l'image
    group_id: Optional[str] = None        # ID du groupe (pour variantes)
    variant_name: Optional[str] = None    # Nom de la variante (ex: "Rouge", "Bleu")


class Product(ProductCreate):
    id: int
    code: str                   # Code unique: #K001, #K002, etc.
    created_at: datetime
    is_available: bool = True
    image_path: Optional[str] = None
    group_id: Optional[str] = None
    variant_name: Optional[str] = None

    class Config:
        from_attributes = True


# === CONVERSATION ===
class ConversationCreate(BaseModel):
    merchant_id: int
    product_id: int
    client_phone: str           # Numéro WhatsApp du client

    @field_validator('client_phone')
    @classmethod
    def validate_client_phone(cls, v):
        return validate_phone_number(v)


class Conversation(ConversationCreate):
    id: int
    status: ConversationStatus = ConversationStatus.ACTIVE
    current_offer: Optional[float] = None   # Dernière offre du client
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# === MESSAGE ===
class MessageCreate(BaseModel):
    conversation_id: int
    content: str
    is_from_client: bool        # True = client, False = bot


class Message(MessageCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# === CONSTANTES ===
MAX_MESSAGE_LENGTH = 2000  # Limite pour éviter abus et coûts API


# === REQUETES API ===
class IncomingMessage(BaseModel):
    """Message entrant depuis WhatsApp"""
    merchant_phone: str         # Numéro du marchand (pour identifier le compte)
    client_phone: str           # Numéro du client
    message: str = Field(..., max_length=MAX_MESSAGE_LENGTH)  # Contenu limité
    product_code: Optional[str] = None  # #K001 si détecté
    client_name: Optional[str] = None   # Nom WhatsApp du client (pushName)

    @field_validator('message')
    @classmethod
    def truncate_message(cls, v):
        """Tronque le message s'il dépasse la limite"""
        if len(v) > MAX_MESSAGE_LENGTH:
            return v[:MAX_MESSAGE_LENGTH]
        return v


class BotResponse(BaseModel):
    """Réponse du bot à envoyer"""
    message: str
    conversation_id: int
    should_notify_merchant: bool = False  # Notifier le marchand?
    notification_reason: Optional[str] = None
    no_response: bool = False  # Si True, ne pas envoyer de message
    images_to_send: Optional[List[dict]] = None  # Images à envoyer (variantes)
    away_mode: bool = False  # Si True, message d'absence automatique
    send_location: bool = False  # Si True, le bridge envoie la localisation APRÈS le texte
    merchant_location: Optional[dict] = None  # Données localisation {latitude, longitude, name, address}
    goodbye_message: Optional[str] = None  # Message de fin envoyé APRÈS tout le reste (deal conclu)
    human_takeover: bool = False  # Si True, l'IA passe la main au marchand humain


class MerchantReply(BaseModel):
    """Réponse manuelle du marchand pour une conversation (human takeover)"""
    merchant_id: int
    conversation_id: int
    client_phone: str
    client_question: str   # La question du client à laquelle on répond
    merchant_answer: str   # La réponse du marchand
    save_to_kb: bool = True  # Sauvegarder automatiquement en KB


# === DEBUG / TEST CHAT ===
class DebugIncomingMessage(IncomingMessage):
    """Message entrant avec flag debug pour l'endpoint de test"""
    debug: bool = True


class DebugBotResponse(BotResponse):
    """Réponse étendue avec trace complète du pipeline AI"""
    debug_trace: Optional[dict] = None  # DebugTracer.to_dict()


# === VITRINE PUBLIQUE ===
class StorefrontProduct(BaseModel):
    """Produit affiché sur la vitrine publique (sans min_price!)"""
    id: int
    code: str
    name: str
    price: float
    description: Optional[str] = None
    image_url: Optional[str] = None
    variant_name: Optional[str] = None
    group_id: Optional[str] = None
    in_stock: bool = True


class StorefrontOrderCreate(BaseModel):
    """Commande depuis la vitrine web"""
    merchant_phone: str
    product_code: str
    client_name: str = Field(..., min_length=2, max_length=100)
    client_phone: str
    message: Optional[str] = Field(None, max_length=500)

    @field_validator('client_phone')
    @classmethod
    def validate_client_phone(cls, v):
        return validate_phone_number(v)
