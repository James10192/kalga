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
