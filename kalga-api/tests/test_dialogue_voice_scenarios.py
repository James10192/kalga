"""Scénarios bout-en-bout NIVEAU VOIX : message → intentions → plan → texte final.

Le pipeline complet ①→⑤ sans réseau (FakeLLM). Vérifie que même un LLM
malveillant/dérapant ne peut plus produire les bugs terrain.
"""
from app.services.dialogue.policy import PolicyContext, decide_plan
from app.services.dialogue.sale_state import SaleState
from app.services.dialogue.speech import SpeechContext, render
from app.services.dialogue.understanding import extract_intents
from app.services.dialogue.llm_protocol import FakeLLMClient


async def speak_through_pipeline(message, state, llm, last_bot=None, **kw):
    defaults = dict(listed_price=10000.0, floor_price=8000.0, current_offer=None,
                    has_variants=True, has_photo=True, stock_out=False,
                    last_bot_price=None)
    defaults.update(kw)
    intents = extract_intents(message, last_bot_message=last_bot)
    plan = decide_plan(intents, PolicyContext(state=state, **defaults))
    sctx = SpeechContext(product_name="Chemise", listed_price=10000.0,
                         floor_price=8000.0, client_message=message)
    return plan, await render(plan, sctx, llm)


async def test_voice_bug2_banco_structurally_impossible():
    """Capture 2 complète : demande photos + LLM qui s'obstine à conclure."""
    rogue = FakeLLMClient(speak_results=[
        "Banco à 10 000 F! On fait comment pour la livraison?",
        "On s'entend pour 10 000 F! Livraison ou tu viens?",
    ])
    plan, text = await speak_through_pipeline("Je veux d'autres photos",
                                              SaleState.NEGOCIATION, rogue)
    assert "banco" not in text.lower() and "livraison" not in text.lower()
    assert plan.new_state == SaleState.NEGOCIATION


async def test_voice_bug1_photo_plus_price_noted():
    plan, text = await speak_through_pipeline(
        "Je veux ça à 9000 et envoie moi plus de photo",
        SaleState.NEGOCIATION, None)   # sans LLM : gabarits
    assert "9 000" in text             # prix noté, dit au client
    assert "modèle" in text.lower()    # variantes annoncées
    assert "livraison" not in text.lower()  # pas de clôture


async def test_voice_legit_conclusion_speaks_delivery():
    plan, text = await speak_through_pipeline(
        "ok pour 9000", SaleState.NEGOCIATION, None, last_bot_price=9000.0)
    assert "9 000" in text and "livraison" in text.lower()


async def test_voice_bug4_cest_loriginal_answers_quality_never_sells():
    """Capture du 2026-06-11 12:21 : « c'est l'original » (réponse à un Statut)
    concluait la vente à 18 000 F. Désormais : réponse qualité, zéro clôture."""
    plan, text = await speak_through_pipeline(
        '[Répond à la photo: "Venez faire votre commande #K023"] c\'est l\'original',
        SaleState.NEGOCIATION, None, current_offer=18000.0)
    assert all(a.type.value != "confirm_deal" for a in plan.actions)
    assert "livraison" not in text.lower() and "magasin" not in text.lower()
    assert "qualité" in text.lower() or "garantit" in text.lower()
    assert plan.new_state == SaleState.NEGOCIATION


async def test_voice_bug5_chosen_variant_confirms_choice_not_catalog():
    """Capture du 2026-06-11 13:14 : réponse à la photo « Modèle Fleur » avec
    « je veux celle la mais il faut revoir le prix » → photo de SA fleur +
    contre-offre. Plus jamais le catalogue entier."""
    plan, text = await speak_through_pipeline(
        '[Répond à la photo: "Modèle Fleur"] je veux celle la mais il faut revoir le prix',
        SaleState.NEGOCIATION, None)
    types = [a.type.value for a in plan.actions]
    assert "send_photo" in types and "send_variants" not in types
    assert "confirm_deal" not in types
    assert "9 000" in text or "9 500" in text or "8 000" in text  # une contre-offre chiffrée
    assert plan.new_state == SaleState.NEGOCIATION


async def test_voice_bug6_full_delivery_handoff():
    """Capture du 2026-06-11 13:38-40 : bascule en livraison + adresse →
    transitions d'état réelles + notification marchand + zéro promesse inventée."""
    # 1. « je veux être livré » en CONCLUSION → demande d'adresse + LOGISTIQUE
    plan1, text1 = await speak_through_pipeline(
        "j'ai changé d'avis je veux être livré", SaleState.CONCLUSION,
        None, current_offer=16000.0)
    assert any(a.type.value == "request_address" for a in plan1.actions)
    assert plan1.new_state == SaleState.LOGISTIQUE_LIVRAISON

    # 2. L'adresse → vente bouclée + marchand notifié + pas de promesse d'horaire
    plan2, text2 = await speak_through_pipeline(
        "Gonwaquville", SaleState.LOGISTIQUE_LIVRAISON, None,
        last_bot="Parfait ! Donne-moi ton adresse de livraison ?")
    assert any(a.type.value == "notify_merchant" for a in plan2.actions)
    assert plan2.new_state == SaleState.APRES_VENTE
    assert "demain" not in text2.lower()
    assert "vendeur" in text2.lower()        # c'est LUI qui organise


async def test_voice_hold_floor_varies_with_seed():
    intents = extract_intents("5000 dernier prix")
    plan = decide_plan(intents, PolicyContext(
        state=SaleState.NEGOCIATION, listed_price=10000.0, floor_price=8000.0,
        current_offer=None, has_variants=True, has_photo=True,
        last_bot_price=8000.0))
    texts = set()
    for seed in range(3):
        sctx = SpeechContext(product_name="Chemise", listed_price=10000.0,
                             floor_price=8000.0, round_seed=seed)
        texts.add(await render(plan, sctx, None))
    assert len(texts) >= 2             # le radin n'entend pas un disque rayé
