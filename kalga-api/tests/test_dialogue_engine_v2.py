"""Tests de la façade v2 puis du branchement chat_service bout-en-bout."""
from app.database.connection import get_connection
from app.database.repositories.product_repo import ProductRepository
from app.services.dialogue.engine import respond


async def _seed(group=False):
    repo = ProductRepository()
    async with get_connection() as db:
        cur = await db.execute(
            "INSERT INTO merchants (name, phone, address, latitude, longitude) "
            "VALUES (?, ?, ?, ?, ?)",
            ("Jolie Bien", "2250100000001", "Bassam", 5.2, -3.7),
        )
        await db.commit()
        merchant_id = cur.lastrowid
    base = await repo.create(merchant_id=merchant_id, name="Chemise", price=10000,
                             min_price=8000, image_path="chemise.jpg",
                             group_id="GRP-V2" if group else None)
    variant = None
    if group:
        variant = await repo.create(merchant_id=merchant_id, name="Chemise - Bleu",
                                    price=10000, min_price=8000, image_path="bleu.jpg",
                                    group_id="GRP-V2", variant_name="Bleu")
    merchant = {"id": merchant_id, "phone": "2250100000001", "name": "Jolie Bien",
                "business_name": "Jolie Bien"}
    return merchant, base, variant


async def test_engine_photo_request_returns_image(temp_db):
    merchant, product, _ = await _seed()
    conv = {"id": 1, "status": "negotiating", "current_offer": None,
            "selected_variant_id": None}
    out = await respond("envoie la photo", conv, product, merchant,
                        history=[{"content": "hello", "is_from_client": True},
                                 {"content": "Salut !", "is_from_client": False}],
                        llm=None)
    assert out is not None
    assert out.images_to_send and out.images_to_send[0]["image_path"] == "chemise.jpg"
    assert out.new_status == "negotiating"


async def test_engine_variants_request_returns_variant_images(temp_db):
    merchant, product, variant = await _seed(group=True)
    conv = {"id": 1, "status": "negotiating", "current_offer": None,
            "selected_variant_id": None}
    out = await respond("je veux d'autres photos", conv, product, merchant,
                        history=[], llm=None)
    assert out.images_to_send and out.images_to_send[0]["image_path"] == "bleu.jpg"
    assert "banco" not in out.message.lower()


async def test_engine_chosen_variant_sends_only_that_image(temp_db):
    """Quand selected_variant_id est mémorisé, la confirmation du choix renvoie
    UNIQUEMENT la photo de cette variante — pas le catalogue."""
    merchant, product, variant = await _seed(group=True)
    conv = {"id": 1, "status": "negotiating", "current_offer": None,
            "selected_variant_id": variant["id"]}
    out = await respond(
        '[Répond à la photo: "Modèle Bleu"] je veux celle la mais il faut revoir le prix',
        conv, product, merchant, history=[], llm=None)
    assert out is not None
    assert len(out.images_to_send) == 1
    assert out.images_to_send[0]["image_path"] == "bleu.jpg"
    assert "banco" not in out.message.lower()
    assert out.new_status == "negotiating"


async def test_engine_cheaper_alternatives_lists_real_catalog(temp_db):
    """Bug n°7 : « d'autres fleurs moins cher » → catalogue RÉEL trié par prix,
    et le prix du produit en cours ne bouge pas."""
    merchant, product, _ = await _seed()          # Chemise à 10 000 F
    repo = ProductRepository()
    await repo.create(merchant_id=merchant["id"], name="Rose simple", price=7000,
                      min_price=6000)
    await repo.create(merchant_id=merchant["id"], name="Bouquet luxe", price=25000,
                      min_price=20000)
    conv = {"id": 1, "status": "negotiating", "current_offer": None,
            "selected_variant_id": None}
    out = await respond("Tu n'aurais pas d'autres fleurs moins cher !?",
                        conv, product, merchant, history=[], llm=None)
    assert out is not None
    assert "Rose simple" in out.message and "7 000" in out.message
    assert "Bouquet luxe" not in out.message       # plus cher → exclu
    assert "9 " not in out.message and "8 " not in out.message[:60]  # pas de rabais du produit courant
    assert out.new_status == "negotiating"


async def test_engine_cheaper_alternatives_honest_when_none(temp_db):
    merchant, product, _ = await _seed()
    conv = {"id": 1, "status": "negotiating", "current_offer": None,
            "selected_variant_id": None}
    out = await respond("Tu n'aurais pas d'autres fleurs moins cher !?",
                        conv, product, merchant, history=[], llm=None)
    assert "meilleure offre" in out.message        # honnête : rien de moins cher


async def test_engine_location_request_sets_flag(temp_db):
    merchant, product, _ = await _seed()
    conv = {"id": 1, "status": "agreed", "current_offer": 9000.0,
            "selected_variant_id": None}
    out = await respond("c'est où le magasin ?", conv, product, merchant,
                        history=[], llm=None)
    assert out.send_location is True
    assert out.new_status == "agreed"      # la localisation ne conclut rien


async def test_engine_memory_extra_reaches_the_voice(temp_db):
    """Les faits LTM passés par chat_service arrivent dans le brief du LLM."""
    from app.services.dialogue.llm_protocol import FakeLLMClient
    merchant, product, _ = await _seed()
    conv = {"id": 1, "status": "negotiating", "current_offer": None,
            "selected_variant_id": None}
    fake = FakeLLMClient(speak_result="Content de te revoir ! La photo arrive 😊")
    out = await respond("envoie la photo", conv, product, merchant,
                        history=[{"content": "hello", "is_from_client": True}],
                        llm=fake, memory_extra="Ce qu'on sait du client : aime le rouge")
    assert out is not None
    assert "aime le rouge" in fake.speak_briefs[0]["memory"]


async def test_engine_system_message_returns_none(temp_db):
    merchant, product, _ = await _seed()
    conv = {"id": 1, "status": "active", "current_offer": None,
            "selected_variant_id": None}
    out = await respond("[📸 Le client a envoyé une photo.]", conv, product,
                        merchant, history=[], llm=None)
    assert out is None


async def test_engine_is_defensive_on_bad_input(temp_db):
    merchant, product, _ = await _seed()
    out = await respond("photo svp", {"status": "???"}, {"name": "X"},  # produit invalide
                        merchant, history=[], llm=None)
    assert out is None                      # jamais d'exception → v1 garde la main


def test_v2_is_the_default_engine(monkeypatch):
    """P5a : v2 est le moteur par défaut (v1 = opt-out explicite, legacy)."""
    monkeypatch.delenv("DIALOGUE_ENGINE", raising=False)
    from app.core.config import Settings
    assert Settings(_env_file=None, jwt_secret_key="x" * 32,
                    admin_password="test-password").dialogue_engine == "v2"


# === Bout-en-bout : handle_incoming_message avec DIALOGUE_ENGINE=v2 ===
# ⚠️ deepseek_api_key est neutralisée (None) dans CHAQUE test e2e : la vraie clé
# est dans .env et _default_llm() construirait sinon un adaptateur RÉSEAU.
# Sans clé → gabarits déterministes, zéro réseau, tests stables.
from app.core.config import settings as app_settings
from app.models.schemas import IncomingMessage
from app.services.chat_service import ChatService


async def _conversation_for(merchant, product, status, history_msgs):
    async with get_connection() as db:
        cur = await db.execute(
            "INSERT INTO conversations (merchant_id, product_id, client_phone, status) "
            "VALUES (?, ?, ?, ?)",
            (merchant["id"], product["id"], "2250700000077", status),
        )
        conv_id = cur.lastrowid
        for content, from_client in history_msgs:
            await db.execute(
                "INSERT INTO messages (conversation_id, content, is_from_client) "
                "VALUES (?, ?, ?)", (conv_id, content, int(from_client)),
            )
        await db.commit()
    return conv_id


async def test_e2e_v2_photo_request_sends_photo_no_goodbye(temp_db, monkeypatch):
    """LE bug des captures, rejoué à travers TOUT le service en v2."""
    monkeypatch.setattr(app_settings, "dialogue_engine", "v2")
    monkeypatch.setattr(app_settings, "deepseek_api_key", None)
    merchant, product, _ = await _seed()
    await _conversation_for(merchant, product, "negotiating",
                            [("je veux ça à 9000", True),
                             ("Je peux te faire 9 500 F !", False)])
    svc = ChatService()
    resp = await svc.handle_incoming_message(IncomingMessage(
        merchant_phone=merchant["phone"], client_phone="2250700000077",
        message="je veux des photos"))
    assert resp.images_to_send, "la photo doit partir"
    assert resp.goodbye_message is None
    assert "banco" not in (resp.message or "").lower()


async def test_e2e_v2_bare_ok_after_priced_bot_concludes(temp_db, monkeypatch):
    monkeypatch.setattr(app_settings, "dialogue_engine", "v2")
    monkeypatch.setattr(app_settings, "deepseek_api_key", None)
    merchant, product, _ = await _seed()
    await _conversation_for(merchant, product, "negotiating",
                            [("9000 ?", True),
                             ("Je peux te faire 9 500 F !", False)])
    svc = ChatService()
    resp = await svc.handle_incoming_message(IncomingMessage(
        merchant_phone=merchant["phone"], client_phone="2250700000077",
        message="ok je prends"))
    assert "9 500" in resp.message
    assert "livraison" in resp.message.lower()


async def test_e2e_v2_full_delivery_handoff_flow(temp_db, monkeypatch):
    """Le parcours complet de la capture 13:38-40, corrigé de bout en bout :
    conclusion → bascule livraison (forme passive) → adresse → APRES_VENTE.
    La conversation reste joignable en pending_delivery (fix get_active)."""
    monkeypatch.setattr(app_settings, "dialogue_engine", "v2")
    monkeypatch.setattr(app_settings, "deepseek_api_key", None)
    merchant, product, _ = await _seed()
    conv_id = await _conversation_for(merchant, product, "negotiating",
                                      [("9000 ?", True),
                                       ("Je peux te faire 9 500 F !", False)])
    svc = ChatService()

    def msg(text):
        return IncomingMessage(merchant_phone=merchant["phone"],
                               client_phone="2250700000077", message=text)

    r1 = await svc.handle_incoming_message(msg("ok je prends"))
    assert "9 500" in r1.message                      # conclusion

    r2 = await svc.handle_incoming_message(msg("j'ai changé d'avis je veux être livré"))
    assert "adresse" in r2.message.lower()            # demande d'adresse

    r3 = await svc.handle_incoming_message(msg("Gonwaquville, près du marché"))
    assert r3.message, "le bot ne doit JAMAIS rester muet sur l'adresse"
    assert "vendeur" in r3.message.lower()            # le marchand prend la main
    assert "demain" not in r3.message.lower()         # zéro promesse inventée

    async with get_connection() as db:
        cur = await db.execute("SELECT status FROM conversations WHERE id = ?", (conv_id,))
        row = await cur.fetchone()
    assert row["status"] == "completed"


async def test_e2e_client_returns_after_closed_sale_is_never_walled(temp_db, monkeypatch):
    """Terrain 15:17 : « Je peux avoir des photos ? » après clôture →
    « PAS DE RÉPONSE - conversation terminée ». La vente conclue doit rester
    une porte OUVERTE : photos, SAV, nouvelle négo."""
    monkeypatch.setattr(app_settings, "dialogue_engine", "v2")
    monkeypatch.setattr(app_settings, "deepseek_api_key", None)
    merchant, product, _ = await _seed()
    await _conversation_for(merchant, product, "completed",
                            [("ok je prends", True),
                             ("Merci pour ton achat !", False)])
    svc = ChatService()
    resp = await svc.handle_incoming_message(IncomingMessage(
        merchant_phone=merchant["phone"], client_phone="2250700000077",
        message="Je peux avoir des photos de l'article ?"))
    assert not resp.no_response, "le client qui revient ne doit JAMAIS être muré"
    assert resp.images_to_send, "la photo doit partir"


async def test_e2e_notification_carries_negotiated_price(temp_db, monkeypatch):
    """Bug terrain n°9 : le marchand recevait le PRIX AFFICHÉ dans la
    notification au lieu du prix négocié. On capture l'appel réel."""
    monkeypatch.setattr(app_settings, "dialogue_engine", "v2")
    monkeypatch.setattr(app_settings, "deepseek_api_key", None)
    merchant, product, _ = await _seed()       # 10 000 F affiché, plancher 8 000
    await _conversation_for(merchant, product, "negotiating",
                            [("hello", True), ("Salut !", False)])
    svc = ChatService()
    recorded = []

    async def fake_notify_sale(**kw):
        recorded.append(kw)
        return True
    monkeypatch.setattr(svc.notifications, "notify_sale", fake_notify_sale)

    def msg(t):
        return IncomingMessage(merchant_phone=merchant["phone"],
                               client_phone="2250700000077", message=t)

    await svc.handle_incoming_message(msg("c'est trop cher"))    # contre → 9 000 persisté
    r2 = await svc.handle_incoming_message(msg("ok je prends"))  # conclut à 9 000
    assert "9 000" in r2.message
    await svc.handle_incoming_message(msg("je veux être livré")) # transition → notification

    assert recorded, "le marchand doit être notifié"
    assert recorded[-1]["price"] == 9000.0, "le prix NÉGOCIÉ, pas le prix affiché"
    assert recorded[-1]["price"] != product["price"]


async def test_e2e_v1_path_untouched_when_flag_off(temp_db, monkeypatch):
    monkeypatch.setattr(app_settings, "dialogue_engine", "v1")
    monkeypatch.setattr(app_settings, "deepseek_api_key", None)
    merchant, product, _ = await _seed()
    await _conversation_for(merchant, product, "negotiating",
                            [("hello", True), ("Salut !", False)])
    svc = ChatService()
    resp = await svc.handle_incoming_message(IncomingMessage(
        merchant_phone=merchant["phone"], client_phone="2250700000077",
        message="envoie la photo"))
    # v1 : l'interception déterministe existante sert déjà la photo
    assert resp.images_to_send
