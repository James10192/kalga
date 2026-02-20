"""
Schémas Pydantic pour les commandes marchand
"""
from pydantic import BaseModel
from typing import Optional
from enum import Enum


class CommandAction(str, Enum):
    """Actions possibles en réponse à une commande"""
    PRODUCT_CREATE_START = "product_create_start"
    PRODUCT_STEP = "product_step"
    PRODUCT_CREATED = "product_created"
    PRODUCT_COMPLETE = "product_complete"
    VARIANT_CREATE_START = "variant_create_start"
    VARIANT_STEP = "variant_step"
    VARIANT_CREATED = "variant_created"
    VARIANT_CONTINUE = "variant_continue"
    VARIANTS_COMPLETE = "variants_complete"
    SALE_COMPLETED = "sale_completed"
    SALE_CANCELLED = "sale_cancelled"
    LIST = "list"
    LIST_EMPTY = "list_empty"
    DELETE = "delete"
    HELP = "help"
    ERROR = "error"
    CANCELLED = "cancelled"
    IGNORED = "ignored"
    ASK_AGAIN = "ask_again"
    PRODUCT_EDIT_START = "product_edit_start"
    PRODUCT_EDIT_STEP = "product_edit_step"
    PRODUCT_EDITED = "product_edited"
    UNKNOWN = "unknown"
    NO_PENDING = "no_pending"


class MerchantMessage(BaseModel):
    """Message entrant du marchand via WhatsApp"""
    merchant_phone: str
    message: str
    image_path: Optional[str] = None


class CommandResponse(BaseModel):
    """Réponse à une commande marchand"""
    response: str
    action: CommandAction
    product_code: Optional[str] = None

    class Config:
        use_enum_values = True


class CreationStep(str, Enum):
    """Étapes de création d'un produit"""
    NAME = "name"
    PRICE = "price"
    MIN_PRICE = "min_price"
    DESCRIPTION = "description"
    IMAGE = "image"
    ASK_VARIANT = "ask_variant"
    VARIANT_NAME = "variant_name"
    VARIANT_IMAGE = "variant_image"
    ASK_ANOTHER_VARIANT = "ask_another_variant"
    EDIT_CHOOSE = "edit_choose"
    EDIT_VALUE = "edit_value"
    EDIT_CONFIRM = "edit_confirm"
