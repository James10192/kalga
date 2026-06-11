"""
Étage ③ — Catalogue d'actions et plan (spec §7).

La politique produit un ActionPlan ORDONNÉ ; l'exécution (P4) le réalise ;
la parole (P3) habille les SEND_TEXT à partir de leurs `facts`.
"""
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple

from .sale_state import SaleState


class ActionType(str, Enum):
    SEND_TEXT = "send_text"                  # facts sémantiques à formuler
    SEND_PHOTO = "send_photo"
    SEND_VARIANTS = "send_variants"
    SEND_LOCATION = "send_location"
    SEND_PAYMENT_INFO = "send_payment_info"
    COUNTER_OFFER = "counter_offer"          # price
    CONFIRM_DEAL = "confirm_deal"            # price — demande livraison/retrait
    REQUEST_ADDRESS = "request_address"
    NOTIFY_MERCHANT = "notify_merchant"      # reason
    HANDOVER_HUMAN = "handover_human"
    END_CONVERSATION = "end_conversation"
    JOIN_WAITLIST = "join_waitlist"


@dataclass(frozen=True)
class Action:
    type: ActionType
    price: Optional[float] = None
    reason: Optional[str] = None
    facts: Tuple[str, ...] = ()


@dataclass
class ActionPlan:
    actions: List[Action]
    new_state: SaleState
    new_offer: Optional[float] = None
