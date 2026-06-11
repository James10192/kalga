"""
Bug terrain n°11 (2026-06-11 16:35) : la session de création vit en mémoire ;
après un redémarrage de l'API, les photos et « fini » du marchand tombaient
dans UNKNOWN — que le bridge jette SILENCIEUSEMENT. Le marchand parlait dans
le vide.

Règle : un message orphelin de session (photo, fini, annuler) reçoit TOUJOURS
une réponse qui explique quoi faire — jamais le silence.
"""
import pytest

from app.modules.merchant_commands.service import MerchantCommandService
from app.modules.merchant_commands.schemas import MerchantMessage, CommandAction
from app.modules.merchant_commands.session_manager import session_manager
from app.database import connection as conn_module


@pytest.fixture
async def merchant(temp_db):
    from app.database import get_db
    db = await get_db()
    merchant_id = await db.create_merchant(
        phone="2250100000001", name="Testeur", business_name="Boutique Test")
    return await db.get_merchant_by_phone("2250100000001")


@pytest.fixture(autouse=True)
def clean_sessions():
    session_manager._sessions.clear()
    yield
    session_manager._sessions.clear()


def _msg(text="", image=None):
    return MerchantMessage(merchant_phone="2250100000001",
                           message=text, image_path=image)


async def test_orphan_photo_gets_helpful_response(merchant):
    """Photo reçue SANS session (ex: API redémarrée) → réponse claire,
    jamais UNKNOWN (que le bridge jette en silence)."""
    svc = MerchantCommandService()
    resp = await svc.process_command(_msg(image="photo123.jpg"))
    assert resp.action != CommandAction.UNKNOWN
    assert resp.response and "produit" in resp.response.lower()


async def test_orphan_fini_gets_helpful_response(merchant):
    svc = MerchantCommandService()
    resp = await svc.process_command(_msg("Fini"))
    assert resp.action != CommandAction.UNKNOWN
    assert resp.response


async def test_orphan_annuler_gets_helpful_response(merchant):
    svc = MerchantCommandService()
    resp = await svc.process_command(_msg("annuler"))
    assert resp.action != CommandAction.UNKNOWN
    assert resp.response


async def test_unknown_text_stays_unknown(merchant):
    # Un texte quelconque hors session reste UNKNOWN (pas de spam) —
    # seuls photo/fini/annuler sont des signaux de session perdue.
    svc = MerchantCommandService()
    resp = await svc.process_command(_msg("Hum vraiment"))
    assert resp.action == CommandAction.UNKNOWN
