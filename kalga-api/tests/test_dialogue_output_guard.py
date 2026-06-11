"""Tests du filet de sortie — aucun langage interdit ne sort."""
from app.services.dialogue.actions import Action, ActionPlan, ActionType
from app.services.dialogue.output_guard import guard_output
from app.services.dialogue.sale_state import SaleState


def _plan(*types, state=SaleState.NEGOCIATION):
    return ActionPlan(actions=[Action(t) for t in types], new_state=state)


def test_closing_language_blocked_outside_conclusion():
    v = guard_output("Banco à 10 000 F! On fait comment pour la livraison?",
                     _plan(ActionType.SEND_VARIANTS), floor_price=8000)
    assert not v.ok and any("cloture" in x for x in v.violations)


def test_closing_language_allowed_with_confirm_deal():
    plan = ActionPlan(actions=[Action(ActionType.CONFIRM_DEAL, price=9000.0)],
                      new_state=SaleState.CONCLUSION)
    v = guard_output("Banco à 9 000 F ! Livraison ou tu passes chercher ?",
                     plan, floor_price=8000)
    assert v.ok


def test_closing_language_allowed_in_logistics_state():
    plan = _plan(ActionType.SEND_LOCATION, state=SaleState.LOGISTIQUE_RETRAIT)
    v = guard_output("On t'attend ! Tu passes chercher quand tu veux.", plan, floor_price=8000)
    assert v.ok


def test_proposing_price_below_floor_blocked():
    v = guard_output("Allez, je peux te faire 7 000 F !",
                     _plan(ActionType.COUNTER_OFFER), floor_price=8000)
    assert not v.ok and any("prix" in x for x in v.violations)


def test_quoting_client_low_price_is_allowed():
    # Citer l'offre basse du client n'est pas la proposer
    v = guard_output("5 000 F c'est un peu bas ! Je peux faire 9 000 F.",
                     _plan(ActionType.COUNTER_OFFER), floor_price=8000)
    assert v.ok


def test_revealing_min_price_concept_blocked():
    v = guard_output("Mon prix minimum c'est 8 000 F, je ne peux pas moins.",
                     _plan(ActionType.COUNTER_OFFER), floor_price=8000)
    assert not v.ok and any("secret" in x for x in v.violations)


def test_clean_text_passes():
    v = guard_output("Je peux te faire 9 000 F, c'est un bon prix !",
                     _plan(ActionType.COUNTER_OFFER), floor_price=8000)
    assert v.ok
