"""Tests du flux BulkVariantCreationHandler."""
import os

from PIL import Image

from app.database import get_db
from app.database.connection import get_connection
from app.database.repositories.product_repo import ProductRepository
from app.modules.merchant_commands.handlers.bulk_variant_creation import (
    BulkVariantCreationHandler,
)
from app.modules.merchant_commands.session_manager import (
    ProductSession, session_manager,
)
from app.modules.merchant_commands.schemas import CreationStep, CommandAction


async def _base_session(group_id="GRP-H1", phone="2250711111111"):
    repo = ProductRepository()
    async with get_connection() as db:
        cur = await db.execute(
            "INSERT INTO merchants (name, phone) VALUES (?, ?)", ("M", phone)
        )
        await db.commit()
        merchant_id = cur.lastrowid
    base = await repo.create(
        merchant_id=merchant_id, name="Sac", price=15000, min_price=12000,
        description=None, group_id=group_id,
    )
    session = ProductSession(
        merchant_phone=phone,
        step=CreationStep.VARIANT_BATCH_PHOTOS,
        data={
            "merchant_id": merchant_id, "name": "Sac", "price": 15000,
            "min_price": 12000, "description": None, "group_id": group_id,
            "original_code": base["code"], "batch_photos": [],
        },
    )
    return merchant_id, session


def _write_upload(filename, color):
    """Écrit une image unie dans le dossier uploads réel utilisé par le handler."""
    from app.modules.merchant_commands.handlers import bulk_variant_creation as mod
    os.makedirs(mod._UPLOADS_DIR, exist_ok=True)
    path = os.path.join(mod._UPLOADS_DIR, filename)
    Image.new("RGB", (80, 80), color).save(path)
    return path


async def test_text_list_creates_variants(temp_db):
    merchant_id, session = await _base_session(phone="2250711111101")
    session.step = CreationStep.VARIANT_BATCH_CONFIRM  # mode liste passe direct
    session.set_data("pending_variants",
                     [{"variant_name": "Rouge", "image_path": None},
                      {"variant_name": "Bleu", "image_path": None}])
    handler = BulkVariantCreationHandler()
    db = await get_db()
    resp = await handler.handle(session, "ok", None, db)
    assert resp.action == CommandAction.VARIANTS_BATCH_CREATED
    repo = ProductRepository()
    products = await repo.get_by_merchant(merchant_id)
    names = {p["name"] for p in products}
    assert "Sac - Rouge" in names and "Sac - Bleu" in names


async def test_batch_photos_buffer_then_confirm(temp_db):
    merchant_id, session = await _base_session(group_id="GRP-H2", phone="2250711111102")
    handler = BulkVariantCreationHandler()
    db = await get_db()

    p1 = _write_upload("h2_red.png", (200, 30, 30))
    p2 = _write_upload("h2_blue.png", (40, 80, 200))
    # Deux photos bufferisées
    await handler.handle(session, "", "h2_red.png", db)
    await handler.handle(session, "", "h2_blue.png", db)
    assert len(session.get_data("batch_photos")) == 2

    # "fini" → passage en confirmation
    resp = await handler.handle(session, "fini", None, db)
    assert session.step == CreationStep.VARIANT_BATCH_CONFIRM
    assert "rouge" in resp.response.lower()
    assert "bleu" in resp.response.lower()

    # "ok" → création
    resp2 = await handler.handle(session, "ok", None, db)
    assert resp2.action == CommandAction.VARIANTS_BATCH_CREATED
    repo = ProductRepository()
    products = await repo.get_by_merchant(merchant_id)
    assert any(p["name"] == "Sac - rouge" for p in products)
    os.remove(p1)
    os.remove(p2)


async def test_batch_confirm_with_correction(temp_db):
    merchant_id, session = await _base_session(group_id="GRP-H3", phone="2250711111103")
    session.step = CreationStep.VARIANT_BATCH_CONFIRM
    session.set_data("pending_variants",
                     [{"variant_name": "rouge", "image_path": None},
                      {"variant_name": "à préciser", "image_path": None}])
    handler = BulkVariantCreationHandler()
    db = await get_db()
    resp = await handler.handle(session, "2=édition limitée", None, db)
    assert resp.action == CommandAction.VARIANTS_BATCH_CREATED
    repo = ProductRepository()
    products = await repo.get_by_merchant(merchant_id)
    assert any(p["name"] == "Sac - édition limitée" for p in products)


async def test_fini_with_no_photo_reasks(temp_db):
    merchant_id, session = await _base_session(group_id="GRP-H4", phone="2250711111104")
    handler = BulkVariantCreationHandler()
    db = await get_db()
    resp = await handler.handle(session, "fini", None, db)
    assert resp.action == CommandAction.ASK_AGAIN
    assert session.step == CreationStep.VARIANT_BATCH_PHOTOS


# === Tests d'intégration (Task 6 : câblage commande + routage) ===
from app.modules.merchant_commands.service import MerchantCommandService
from app.modules.merchant_commands.schemas import MerchantMessage


async def test_command_variantes_creates_list(temp_db):
    repo = ProductRepository()
    async with get_connection() as db:
        cur = await db.execute(
            "INSERT INTO merchants (name, phone) VALUES (?, ?)", ("M", "2250799999999")
        )
        await db.commit()
        merchant_id = cur.lastrowid
    base = await repo.create(
        merchant_id=merchant_id, name="Sac", price=15000, min_price=12000,
        description=None,
    )
    service = MerchantCommandService()
    msg = MerchantMessage(
        merchant_phone="2250799999999",
        message=f"variantes {base['code']} rouge, bleu, noir",
    )
    resp = await service.process_command(msg)
    assert resp.action == CommandAction.VARIANTS_BATCH_CREATED
    products = await repo.get_by_merchant(merchant_id)
    names = {p["name"] for p in products}
    assert {"Sac - rouge", "Sac - bleu", "Sac - noir"} <= names


async def test_ask_variant_comma_routes_to_bulk(temp_db):
    """Au step ASK_VARIANT, une liste avec virgule crée les variantes en lot."""
    repo = ProductRepository()
    async with get_connection() as db:
        cur = await db.execute(
            "INSERT INTO merchants (name, phone) VALUES (?, ?)", ("M", "2250788888888")
        )
        await db.commit()
        merchant_id = cur.lastrowid
    base = await repo.create(
        merchant_id=merchant_id, name="Sac", price=15000, min_price=12000,
        description=None,
    )
    session_manager.create(
        merchant_phone="2250788888888",
        step=CreationStep.ASK_VARIANT,
        data={"merchant_id": merchant_id, "name": "Sac", "price": 15000,
              "min_price": 12000, "description": None,
              "product_code": base["code"], "product_id": base["id"]},
    )
    service = MerchantCommandService()
    msg = MerchantMessage(merchant_phone="2250788888888", message="rouge, bleu")
    resp = await service.process_command(msg)
    assert resp.action == CommandAction.VARIANTS_BATCH_CREATED
