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
