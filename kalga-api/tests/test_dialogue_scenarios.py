"""Scénarios bout-en-bout au niveau cerveau : message brut → intentions → plan.

Rejoue les conversations réelles (captures WhatsApp) à travers
extract_intents + decide_plan, sans LLM ni DB. Le comportement attendu
est celui validé par le marchand.
"""
from app.services.dialogue.actions import ActionType
from app.services.dialogue.policy import PolicyContext, decide_plan
from app.services.dialogue.sale_state import SaleState
from app.services.dialogue.understanding import extract_intents


def think(message, state, last_bot=None, **ctx_kw):
    """Pipeline cerveau : compréhension → décision."""
    defaults = dict(listed_price=10000.0, floor_price=8000.0, current_offer=None,
                    has_variants=True, has_photo=True, stock_out=False,
                    last_bot_price=None)
    defaults.update(ctx_kw)
    intents = extract_intents(message, last_bot_message=last_bot)
    return decide_plan(intents, PolicyContext(state=state, **defaults))


def test_scenario_bug1_full():
    """Capture 1 : « Je veux ça à 9000 et envoie moi plus de photo »."""
    plan = think("Je veux ça à 9000 et envoie moi plus de photo", SaleState.NEGOCIATION)
    types = [a.type for a in plan.actions]
    assert ActionType.SEND_VARIANTS in types          # la demande visuelle d'abord
    assert ActionType.CONFIRM_DEAL not in types        # JAMAIS de clôture ici
    assert plan.new_offer == 9000.0                    # le prix est noté
    # ... puis le client confirme au tour suivant :
    plan2 = think("ok", SaleState.NEGOCIATION, last_bot="Pour 9 000 F c'est bon !",
                  last_bot_price=9000.0)
    assert plan2.actions[-1].type == ActionType.CONFIRM_DEAL
    assert plan2.actions[-1].price == 9000.0


def test_scenario_bug2_photos_then_no_banco():
    """Capture 2 : « Je veux d'autres photos » 2× — photos servies, zéro Banco."""
    for _ in range(2):
        plan = think("Je veux d'autres photos", SaleState.NEGOCIATION, has_variants=True)
        types = [a.type for a in plan.actions]
        assert types == [ActionType.SEND_VARIANTS]
        assert plan.new_state == SaleState.NEGOCIATION


def test_scenario_bug3_hello_on_status():
    """Capture 3 : « hello » sur un Statut → accueil, pas de photo."""
    plan = think('[Répond à la photo: "#K053"] Hello', SaleState.ACCUEIL)
    assert [a.type for a in plan.actions] == [ActionType.SEND_TEXT]
    assert "greeting" in plan.actions[0].facts
    assert plan.new_state == SaleState.RENSEIGNEMENT


def test_scenario_oui_interest_never_sells():
    """« Oui » à « ça t'intéresse ? » → clarification, zéro vente."""
    plan = think("Oui", SaleState.RENSEIGNEMENT, last_bot="Ça t'intéresse ?")
    assert all(a.type != ActionType.CONFIRM_DEAL for a in plan.actions)


def test_scenario_nominal_full_sale():
    """Parcours nominal : accueil → info → négo → conclusion → livraison."""
    p1 = think("bonjour, c'est disponible ?", SaleState.ACCUEIL)
    assert all(a.type != ActionType.CONFIRM_DEAL for a in p1.actions)

    p2 = think("envoie la photo", SaleState.RENSEIGNEMENT)
    assert p2.actions[0].type == ActionType.SEND_PHOTO

    p3 = think("je te donne 5000", SaleState.RENSEIGNEMENT)
    assert p3.actions[-1].type == ActionType.COUNTER_OFFER
    assert p3.actions[-1].price == 9000.0
    assert p3.new_state == SaleState.NEGOCIATION

    p4 = think("ok pour 9000", SaleState.NEGOCIATION, last_bot_price=9000.0)
    assert p4.actions[-1].type == ActionType.CONFIRM_DEAL
    assert p4.new_state == SaleState.CONCLUSION

    p5 = think("je veux me faire livrer", SaleState.CONCLUSION)
    assert p5.actions[0].type == ActionType.REQUEST_ADDRESS
    assert p5.new_state == SaleState.LOGISTIQUE_LIVRAISON

    p6 = think("cocody angré 7e tranche", SaleState.LOGISTIQUE_LIVRAISON,
               last_bot="Parfait ! Donne-moi ton adresse de livraison ?")
    assert any(a.type == ActionType.NOTIFY_MERCHANT for a in p6.actions)
    assert p6.new_state == SaleState.APRES_VENTE


def test_scenario_switch_pickup_to_delivery():
    """L'oubli de la capture 1 : changer retrait → livraison reste possible."""
    plan = think("finalement je veux me faire livrer", SaleState.LOGISTIQUE_RETRAIT)
    assert plan.actions[0].type == ActionType.REQUEST_ADDRESS
    assert plan.new_state == SaleState.LOGISTIQUE_LIVRAISON


def test_scenario_radin_holds_floor_forever():
    """Client radin : le bot tient le plancher sans jamais casser le prix."""
    plan = think("5000 dernier prix", SaleState.NEGOCIATION, last_bot_price=8000.0)
    assert plan.actions[-1].type == ActionType.COUNTER_OFFER
    assert plan.actions[-1].price == 8000.0
    assert "hold_floor" in plan.actions[-1].facts
