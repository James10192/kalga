"""
Étage ③ — Politique de dialogue (spec §6, §7).

decide_plan(intents, ctx) -> ActionPlan : fonction PURE. C'est ici — et nulle
part ailleurs — que se décident les actions et les transitions d'état. Le LLM
n'y a aucun droit de regard ; il habillera le plan (P3).

Invariants gravés (décisions du marchand) :
- toute demande (ASK_*) est honorée, dans tous les états, avant la vente ;
- CONFIRM_DEAL impossible si une demande arrive dans le même message ;
- un « accord » sans prix sur la table ne conclut jamais ;
- une contre-offre client annule tout pré-accord (retour NÉGOCIATION) ;
- livraison ↔ retrait modifiable en LOGISTIQUE.
"""
from dataclasses import dataclass
from typing import List, Optional

from .actions import Action, ActionPlan, ActionType
from .intents import Intent, IntentType
from .negotiation import decide as negotiate
from .sale_state import SaleState

_REQUEST_TYPES = {
    IntentType.ASK_PHOTO, IntentType.ASK_OTHER_PHOTOS, IntentType.ASK_VARIANTS,
    IntentType.ASK_OTHER_PRODUCTS, IntentType.CHOOSE_VARIANT, IntentType.ASK_INFO,
    IntentType.ASK_LOCATION, IntentType.ASK_PAYMENT, IntentType.ASK_DELIVERY_INFO,
}
_DEAL_STATES = {SaleState.CONCLUSION, SaleState.LOGISTIQUE_LIVRAISON,
                SaleState.LOGISTIQUE_RETRAIT}


@dataclass
class PolicyContext:
    state: SaleState
    listed_price: float
    floor_price: float                 # plancher effectif (fidélité déjà appliquée)
    current_offer: Optional[float]     # prix sur la table (accord de principe)
    has_variants: bool
    has_photo: bool
    stock_out: bool = False
    last_bot_price: Optional[float] = None  # dernier prix chiffré par le bot


def _handle_request(intent: Intent, ctx: PolicyContext) -> Action:
    t = intent.type
    if t == IntentType.ASK_PHOTO:
        return Action(ActionType.SEND_PHOTO)
    if t == IntentType.ASK_OTHER_PHOTOS:
        return Action(ActionType.SEND_VARIANTS) if ctx.has_variants \
            else Action(ActionType.SEND_PHOTO, facts=("only_photo",))
    if t == IntentType.ASK_VARIANTS:
        return Action(ActionType.SEND_VARIANTS)
    if t == IntentType.CHOOSE_VARIANT:
        # Confirmer SON choix : renvoyer la photo de SA variante uniquement
        # (l'exécution résout l'image via selected_variant_id, déjà mémorisé
        # par chat_service._find_and_save_selected_variant).
        return Action(ActionType.SEND_PHOTO, facts=("chosen_variant",),
                      reason=intent.text)
    if t == IntentType.ASK_OTHER_PRODUCTS:
        return Action(ActionType.SEND_TEXT, facts=("catalogue",))
    if t == IntentType.ASK_LOCATION:
        return Action(ActionType.SEND_LOCATION)
    if t == IntentType.ASK_PAYMENT:
        return Action(ActionType.SEND_PAYMENT_INFO)
    if t == IntentType.ASK_DELIVERY_INFO:
        return Action(ActionType.SEND_TEXT, facts=("delivery_info",))
    # ASK_INFO
    subject = f"info:{intent.text}" if intent.text else "info"
    return Action(ActionType.SEND_TEXT, facts=(subject,))


def decide_plan(intents: List[Intent], ctx: PolicyContext) -> ActionPlan:
    actions: List[Action] = []
    state = ctx.state
    offer = ctx.current_offer

    types = {i.type for i in intents}
    has_request = bool(types & _REQUEST_TYPES)

    # 0) Signaux prioritaires
    if IntentType.CORRECTION in types:
        actions.append(Action(ActionType.SEND_TEXT, facts=("correction",)))
    if IntentType.FRUSTRATION in types:
        actions.append(Action(ActionType.SEND_TEXT, facts=("apaisement",)))
    if IntentType.HUMAN_REQUEST in types:
        actions.append(Action(ActionType.HANDOVER_HUMAN))
        actions.append(Action(ActionType.NOTIFY_MERCHANT, reason="human_request"))
        return ActionPlan(actions=actions, new_state=state, new_offer=offer)

    # 1) Demandes du client — toujours honorées, d'abord
    for intent in intents:
        if intent.type in _REQUEST_TYPES:
            actions.append(_handle_request(intent, ctx))

    # 2) Rupture de stock : pas de transactionnel, proposer la liste d'attente
    if ctx.stock_out and (types & {IntentType.PRICE_OFFER, IntentType.ACCEPT_PRICE}):
        actions.append(Action(ActionType.SEND_TEXT, facts=("out_of_stock",)))
        actions.append(Action(ActionType.JOIN_WAITLIST))
        return ActionPlan(actions=actions, new_state=state, new_offer=offer)

    # 3) Transactionnel (verrou de CONCLUSION)
    for intent in intents:
        if intent.type == IntentType.PRICE_OFFER:
            decision = negotiate(intent.amount, ctx.listed_price,
                                 ctx.floor_price, ctx.last_bot_price)
            if decision.kind == "accept":
                offer = decision.price
                if has_request:
                    # Verrou : pas de clôture avec une demande en attente —
                    # on note le prix, le client confirmera au tour suivant.
                    actions.append(Action(ActionType.SEND_TEXT,
                                          facts=("price_ok_pending",), price=decision.price))
                    state = SaleState.NEGOCIATION
                else:
                    actions.append(Action(ActionType.CONFIRM_DEAL, price=decision.price))
                    state = SaleState.CONCLUSION
            else:
                kind = "hold_floor" if decision.kind == "hold_floor" else "counter"
                actions.append(Action(ActionType.COUNTER_OFFER, price=decision.price,
                                      facts=(kind,)))
                state = SaleState.NEGOCIATION
                offer = None  # plus d'accord sur la table

        elif intent.type == IntentType.ACCEPT_PRICE:
            amount = intent.amount if intent.amount is not None else ctx.last_bot_price
            if amount is None:
                actions.append(Action(ActionType.SEND_TEXT, facts=("clarify_deal",)))
                continue
            if amount < ctx.floor_price:
                decision = negotiate(amount, ctx.listed_price,
                                     ctx.floor_price, ctx.last_bot_price)
                actions.append(Action(ActionType.COUNTER_OFFER, price=decision.price,
                                      facts=("counter",)))
                state = SaleState.NEGOCIATION
                offer = None
            elif has_request:
                offer = float(amount)
                actions.append(Action(ActionType.SEND_TEXT,
                                      facts=("price_ok_pending",), price=float(amount)))
                state = SaleState.NEGOCIATION
            else:
                offer = float(amount)
                actions.append(Action(ActionType.CONFIRM_DEAL, price=float(amount)))
                state = SaleState.CONCLUSION

    # 4) Logistique
    for intent in intents:
        if intent.type == IntentType.CHOOSE_DELIVERY:
            if state in _DEAL_STATES:
                actions.append(Action(ActionType.REQUEST_ADDRESS))
                state = SaleState.LOGISTIQUE_LIVRAISON
            else:
                actions.append(Action(ActionType.SEND_TEXT, facts=("delivery_noted",)))
        elif intent.type == IntentType.CHOOSE_PICKUP:
            if state in _DEAL_STATES:
                actions.append(Action(ActionType.SEND_LOCATION))
                actions.append(Action(ActionType.NOTIFY_MERCHANT, reason="pickup"))
                state = SaleState.LOGISTIQUE_RETRAIT
            else:
                actions.append(Action(ActionType.SEND_LOCATION))
        elif intent.type == IntentType.GIVE_ADDRESS and state in (
                SaleState.LOGISTIQUE_LIVRAISON, SaleState.CONCLUSION):
            # Adresse acceptée dès la CONCLUSION aussi (le client peut la donner
            # avant que l'état logistique soit posé — vu sur le terrain).
            actions.append(Action(ActionType.SEND_TEXT, facts=("address_confirmed",),
                                  reason=intent.text))
            actions.append(Action(ActionType.NOTIFY_MERCHANT, reason="delivery_address"))
            state = SaleState.APRES_VENTE

    # 5) Flux social
    if IntentType.GREETING in types and not actions:
        actions.append(Action(ActionType.SEND_TEXT, facts=("greeting",)))
        if state == SaleState.ACCUEIL:
            state = SaleState.RENSEIGNEMENT
    if IntentType.GOODBYE in types:
        actions.append(Action(ActionType.END_CONVERSATION))
        state = SaleState.FIN

    if not actions:
        actions.append(Action(ActionType.SEND_TEXT, facts=("clarify",)))
    return ActionPlan(actions=actions, new_state=state, new_offer=offer)
