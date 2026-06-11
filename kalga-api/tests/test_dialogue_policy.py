"""Tests de la politique de dialogue (et du catalogue d'actions)."""
from app.services.dialogue.actions import Action, ActionPlan, ActionType
from app.services.dialogue.sale_state import SaleState


def test_action_is_frozen_and_defaults():
    a = Action(ActionType.SEND_PHOTO)
    assert a.price is None and a.facts == ()


def test_action_plan_holds_actions_state_offer():
    plan = ActionPlan(
        actions=[Action(ActionType.COUNTER_OFFER, price=9000.0)],
        new_state=SaleState.NEGOCIATION,
        new_offer=9000.0,
    )
    assert plan.actions[0].price == 9000.0
    assert plan.new_state is SaleState.NEGOCIATION


# === Politique : demandes du client ===
from app.services.dialogue.intents import Intent, IntentType
from app.services.dialogue.policy import PolicyContext, decide_plan


def _ctx(state=SaleState.RENSEIGNEMENT, **kw):
    defaults = dict(listed_price=10000.0, floor_price=8000.0, current_offer=None,
                    has_variants=False, has_photo=True, stock_out=False,
                    last_bot_price=None)
    defaults.update(kw)
    return PolicyContext(state=state, **defaults)


def test_ask_photo_yields_send_photo():
    plan = decide_plan([Intent(IntentType.ASK_PHOTO)], _ctx())
    assert plan.actions[0].type == ActionType.SEND_PHOTO
    assert plan.new_state == SaleState.RENSEIGNEMENT


def test_ask_other_photos_routes_by_variants():
    p1 = decide_plan([Intent(IntentType.ASK_OTHER_PHOTOS)], _ctx(has_variants=True))
    assert p1.actions[0].type == ActionType.SEND_VARIANTS
    p2 = decide_plan([Intent(IntentType.ASK_OTHER_PHOTOS)], _ctx(has_variants=False))
    assert p2.actions[0].type == ActionType.SEND_PHOTO


def test_ask_location_never_concludes():
    plan = decide_plan([Intent(IntentType.ASK_LOCATION)], _ctx(state=SaleState.NEGOCIATION))
    assert plan.actions[0].type == ActionType.SEND_LOCATION
    assert plan.new_state == SaleState.NEGOCIATION


def test_ask_payment_and_info_and_delivery_info():
    assert decide_plan([Intent(IntentType.ASK_PAYMENT)], _ctx()).actions[0].type == ActionType.SEND_PAYMENT_INFO
    info = decide_plan([Intent(IntentType.ASK_INFO, text="prix")], _ctx()).actions[0]
    assert info.type == ActionType.SEND_TEXT and "info:prix" in info.facts
    dlv = decide_plan([Intent(IntentType.ASK_DELIVERY_INFO)], _ctx()).actions[0]
    assert dlv.type == ActionType.SEND_TEXT and "delivery_info" in dlv.facts


def test_photo_request_honored_even_in_conclusion():
    # Règle transverse marchand : photo demandée → photo, TOUJOURS
    plan = decide_plan([Intent(IntentType.ASK_PHOTO)], _ctx(state=SaleState.CONCLUSION))
    assert plan.actions[0].type == ActionType.SEND_PHOTO
    assert plan.new_state == SaleState.CONCLUSION


# === Transactionnel : le verrou de CONCLUSION ===

def test_offer_above_floor_alone_confirms_deal():
    plan = decide_plan([Intent(IntentType.PRICE_OFFER, amount=9000.0)],
                       _ctx(state=SaleState.NEGOCIATION))
    assert plan.actions[-1].type == ActionType.CONFIRM_DEAL
    assert plan.actions[-1].price == 9000.0
    assert plan.new_state == SaleState.CONCLUSION
    assert plan.new_offer == 9000.0


def test_bug1_offer_plus_photo_never_concludes():
    """Bug terrain n°1 au niveau cerveau : photo + 9000 → photo + prix noté, PAS de clôture."""
    intents = [Intent(IntentType.ASK_OTHER_PHOTOS), Intent(IntentType.PRICE_OFFER, amount=9000.0)]
    plan = decide_plan(intents, _ctx(state=SaleState.NEGOCIATION, has_variants=True))
    types = [a.type for a in plan.actions]
    assert ActionType.SEND_VARIANTS in types
    assert ActionType.CONFIRM_DEAL not in types
    assert any(a.type == ActionType.SEND_TEXT and "price_ok_pending" in a.facts
               for a in plan.actions)
    assert plan.new_state == SaleState.NEGOCIATION  # pas conclu
    assert plan.new_offer == 9000.0                  # mais prix noté


def test_low_offer_counters():
    plan = decide_plan([Intent(IntentType.PRICE_OFFER, amount=5000.0)],
                       _ctx(state=SaleState.NEGOCIATION))
    assert plan.actions[-1].type == ActionType.COUNTER_OFFER
    assert plan.actions[-1].price == 9000.0  # milieu(10000, 8000)
    assert plan.new_state == SaleState.NEGOCIATION


def test_accept_with_amount_confirms():
    plan = decide_plan([Intent(IntentType.ACCEPT_PRICE, amount=9000.0)],
                       _ctx(state=SaleState.NEGOCIATION))
    assert plan.actions[-1].type == ActionType.CONFIRM_DEAL
    assert plan.new_state == SaleState.CONCLUSION


def test_bare_accept_with_bot_price_confirms_at_that_price():
    plan = decide_plan([Intent(IntentType.ACCEPT_PRICE)],
                       _ctx(state=SaleState.NEGOCIATION, last_bot_price=9500.0))
    assert plan.actions[-1].type == ActionType.CONFIRM_DEAL
    assert plan.actions[-1].price == 9500.0


def test_bare_accept_without_any_price_never_concludes():
    """Le « oui » sans prix sur la table → clarification, jamais de vente."""
    plan = decide_plan([Intent(IntentType.ACCEPT_PRICE)], _ctx(state=SaleState.RENSEIGNEMENT))
    assert all(a.type != ActionType.CONFIRM_DEAL for a in plan.actions)
    assert any("clarify_deal" in a.facts for a in plan.actions if a.type == ActionType.SEND_TEXT)


def test_accept_with_pending_request_defers_conclusion():
    intents = [Intent(IntentType.ASK_PHOTO), Intent(IntentType.ACCEPT_PRICE, amount=9000.0)]
    plan = decide_plan(intents, _ctx(state=SaleState.NEGOCIATION))
    types = [a.type for a in plan.actions]
    assert ActionType.SEND_PHOTO in types and ActionType.CONFIRM_DEAL not in types
    assert plan.new_offer == 9000.0


def test_new_offer_in_conclusion_cancels_agreement():
    plan = decide_plan([Intent(IntentType.PRICE_OFFER, amount=8500.0)],
                       _ctx(state=SaleState.CONCLUSION, current_offer=9500.0))
    assert plan.actions[-1].type == ActionType.CONFIRM_DEAL or plan.new_state == SaleState.CONCLUSION
    # 8500 ≥ plancher → ré-accord direct au nouveau prix
    assert plan.new_offer == 8500.0


def test_accept_below_floor_counters():
    plan = decide_plan([Intent(IntentType.ACCEPT_PRICE, amount=5000.0)],
                       _ctx(state=SaleState.NEGOCIATION))
    assert plan.actions[-1].type == ActionType.COUNTER_OFFER
    assert plan.new_state == SaleState.NEGOCIATION


# === Logistique, flux & signaux ===

def test_choose_delivery_after_deal_requests_address():
    plan = decide_plan([Intent(IntentType.CHOOSE_DELIVERY)], _ctx(state=SaleState.CONCLUSION))
    assert plan.actions[0].type == ActionType.REQUEST_ADDRESS
    assert plan.new_state == SaleState.LOGISTIQUE_LIVRAISON


def test_switch_pickup_to_delivery_in_logistics():
    """Bug terrain : « Je veux me faire livré » après un retrait — désormais accepté."""
    plan = decide_plan([Intent(IntentType.CHOOSE_DELIVERY)],
                       _ctx(state=SaleState.LOGISTIQUE_RETRAIT))
    assert plan.actions[0].type == ActionType.REQUEST_ADDRESS
    assert plan.new_state == SaleState.LOGISTIQUE_LIVRAISON


def test_choose_pickup_after_deal_sends_location_and_notifies():
    plan = decide_plan([Intent(IntentType.CHOOSE_PICKUP)], _ctx(state=SaleState.CONCLUSION))
    types = [a.type for a in plan.actions]
    assert ActionType.SEND_LOCATION in types and ActionType.NOTIFY_MERCHANT in types
    assert plan.new_state == SaleState.LOGISTIQUE_RETRAIT


def test_choose_pickup_without_deal_just_sends_location():
    plan = decide_plan([Intent(IntentType.CHOOSE_PICKUP)], _ctx(state=SaleState.RENSEIGNEMENT))
    assert plan.actions[0].type == ActionType.SEND_LOCATION
    assert plan.new_state == SaleState.RENSEIGNEMENT


def test_give_address_completes_logistics():
    plan = decide_plan([Intent(IntentType.GIVE_ADDRESS, text="cocody angré")],
                       _ctx(state=SaleState.LOGISTIQUE_LIVRAISON))
    types = [a.type for a in plan.actions]
    assert ActionType.NOTIFY_MERCHANT in types
    assert plan.new_state == SaleState.APRES_VENTE


def test_goodbye_ends():
    plan = decide_plan([Intent(IntentType.GOODBYE)], _ctx())
    assert plan.actions[-1].type == ActionType.END_CONVERSATION
    assert plan.new_state == SaleState.FIN


def test_greeting_opens_conversation():
    plan = decide_plan([Intent(IntentType.GREETING)], _ctx(state=SaleState.ACCUEIL))
    a = plan.actions[0]
    assert a.type == ActionType.SEND_TEXT and "greeting" in a.facts
    assert plan.new_state == SaleState.RENSEIGNEMENT


def test_frustration_prepends_apaisement():
    intents = [Intent(IntentType.FRUSTRATION), Intent(IntentType.PRICE_OFFER, amount=5000.0)]
    plan = decide_plan(intents, _ctx(state=SaleState.NEGOCIATION))
    assert plan.actions[0].type == ActionType.SEND_TEXT and "apaisement" in plan.actions[0].facts
    assert plan.actions[-1].type == ActionType.COUNTER_OFFER


def test_human_request_hands_over():
    plan = decide_plan([Intent(IntentType.HUMAN_REQUEST)], _ctx())
    types = [a.type for a in plan.actions]
    assert ActionType.HANDOVER_HUMAN in types and ActionType.NOTIFY_MERCHANT in types


def test_correction_apologizes():
    plan = decide_plan([Intent(IntentType.CORRECTION)], _ctx())
    assert any("correction" in a.facts for a in plan.actions if a.type == ActionType.SEND_TEXT)


def test_stock_out_offers_waitlist_instead_of_deal():
    plan = decide_plan([Intent(IntentType.PRICE_OFFER, amount=9000.0)],
                       _ctx(state=SaleState.RENSEIGNEMENT, stock_out=True))
    types = [a.type for a in plan.actions]
    assert ActionType.JOIN_WAITLIST in types and ActionType.CONFIRM_DEAL not in types


def test_unclear_clarifies():
    plan = decide_plan([Intent(IntentType.UNCLEAR)], _ctx())
    assert any("clarify" in a.facts for a in plan.actions)


def test_choose_variant_sends_only_chosen_photo_and_negotiates():
    """Bug terrain n°5 : choix d'une variante + « revoir le prix » →
    photo de SA variante + contre-offre — JAMAIS le catalogue entier."""
    intents = [Intent(IntentType.CHOOSE_VARIANT, text="Fleur"),
               Intent(IntentType.PRICE_OFFER)]
    plan = decide_plan(intents, _ctx(state=SaleState.NEGOCIATION, has_variants=True))
    types = [a.type for a in plan.actions]
    assert ActionType.SEND_PHOTO in types
    assert ActionType.SEND_VARIANTS not in types
    assert ActionType.COUNTER_OFFER in types
    assert ActionType.CONFIRM_DEAL not in types
    photo = next(a for a in plan.actions if a.type == ActionType.SEND_PHOTO)
    assert "chosen_variant" in photo.facts and photo.reason == "Fleur"
