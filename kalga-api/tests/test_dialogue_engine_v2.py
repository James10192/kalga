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


async def test_engine_location_request_sets_flag(temp_db):
    merchant, product, _ = await _seed()
    conv = {"id": 1, "status": "agreed", "current_offer": 9000.0,
            "selected_variant_id": None}
    out = await respond("c'est où le magasin ?", conv, product, merchant,
                        history=[], llm=None)
    assert out.send_location is True
    assert out.new_status == "agreed"      # la localisation ne conclut rien


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
