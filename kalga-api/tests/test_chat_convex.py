"""
Tests d'intégration du chemin chat Convex-backed (plan 004).

Exercent les fonctions grossières Convex (`internal/chat:getContext`,
`internal/chat:commitTurn`, `internal/inventory:checkProduct`,
`internal/followups:scheduleFollowup`) via le client Python `ConvexBackendClient`,
pointés sur le déploiement de dev (`CONVEX_URL`). DeepSeek n'est pas sollicité :
on teste la PERSISTANCE et l'ATOMICITÉ côté Convex, pas le cerveau.

Les tests sont auto-suffisants : ils utilisent un numéro client de test unique
(préfixe `22588...`), créent puis re-lisent leurs propres données, et sont
idempotents. Ils sont SKIPPÉS si `CONVEX_URL` n'est pas configurée (CI sans
déploiement). Le marchand `demo` (slug `demo`, phone `2250700000000`) et le
catalogue (`SNK01`, `MTR01`...) sont supposés seedés (`npx convex run seed:run`).
"""
import uuid

import pytest

from app.core.config import settings
from app.infrastructure.convex_client import ConvexBackendClient

pytestmark = pytest.mark.skipif(
    not settings.convex_url,
    reason="CONVEX_URL non configurée — tests d'intégration Convex désactivés.",
)

DEMO_MERCHANT_PHONE = "2250700000000"
PRODUCT_CODE = "SNK01"


@pytest.fixture(scope="module")
def convex() -> ConvexBackendClient:
    return ConvexBackendClient(
        url=settings.convex_url,
        admin_key=settings.convex_admin_key,
        internal_key=settings.internal_api_key,
    )


def _unique_client() -> str:
    """Numéro client de test unique (évite toute collision entre runs)."""
    return "22588" + uuid.uuid4().hex[:9]


async def test_checkproduct_returns_stock_and_merchant(convex):
    """checkProduct renvoie le produit enrichi (stock + marchand rattaché)."""
    res = await convex.query(
        "internal/inventory:checkProduct", {"code": PRODUCT_CODE}
    )
    assert res is not None, "Produit SNK01 introuvable — seed manquant ?"
    assert res["product"]["code"] == PRODUCT_CODE
    assert res["stockStatus"]["isUnlimited"] is True  # SNK01 = stock -1
    assert res["merchantName"]  # marchand rattaché présent


async def test_getcontext_resolves_merchant_and_history(convex):
    """getContext renvoie le marchand + la conversation seedée + son historique."""
    ctx = await convex.query(
        "internal/chat:getContext",
        {
            "merchantPhone": DEMO_MERCHANT_PHONE,
            "clientPhone": "2250500000001",  # client seedé en négo
            "productCode": PRODUCT_CODE,
        },
    )
    assert ctx["merchant"] is not None
    assert ctx["conversation"] is not None
    assert ctx["conversation"]["status"] == "negotiating"
    assert len(ctx["history"]) >= 2  # messages seedés


async def test_committurn_ingests_and_persists(convex):
    """
    Happy path ingestion : un tour entrant crée la conversation et persiste
    message client + message bot atomiquement (parité write-path).
    """
    client = _unique_client()

    # Contexte initial : aucune conversation pour ce client neuf.
    ctx = await convex.query(
        "internal/chat:getContext",
        {
            "merchantPhone": DEMO_MERCHANT_PHONE,
            "clientPhone": client,
            "productCode": PRODUCT_CODE,
        },
    )
    assert ctx["conversation"] is None
    merchant_id = ctx["merchant"]["_id"]
    product_id = ctx["product"]["_id"]

    res = await convex.mutation(
        "internal/chat:commitTurn",
        {
            "merchantId": merchant_id,
            "productId": product_id,
            "clientPhone": client,
            "clientMessage": "Bonjour, le SNK01 est dispo ?",
            "botMessage": "Oui ! Les Sneakers Blanches sont à 25 000 FCFA.",
            "newStatus": "active",
        },
    )
    assert res["created"] is True
    assert res["messagesPersisted"] == 2

    # Re-lecture : conversation créée avec ses 2 messages.
    ctx2 = await convex.query(
        "internal/chat:getContext",
        {
            "merchantPhone": DEMO_MERCHANT_PHONE,
            "clientPhone": client,
            "productCode": PRODUCT_CODE,
        },
    )
    assert ctx2["conversation"]["status"] == "active"
    assert len(ctx2["history"]) == 2


async def test_committurn_status_transition_negotiation(convex):
    """
    Négo simple : un second tour sur la même conversation met à jour le statut
    (active -> negotiating) et l'offre courante, sans recréer de conversation.
    """
    client = _unique_client()
    ctx = await convex.query(
        "internal/chat:getContext",
        {"merchantPhone": DEMO_MERCHANT_PHONE, "clientPhone": client, "productCode": PRODUCT_CODE},
    )
    merchant_id = ctx["merchant"]["_id"]
    product_id = ctx["product"]["_id"]

    first = await convex.mutation(
        "internal/chat:commitTurn",
        {
            "merchantId": merchant_id,
            "productId": product_id,
            "clientPhone": client,
            "clientMessage": "Salut",
            "botMessage": "Bonjour !",
            "newStatus": "active",
        },
    )
    conv_id = first["conversationId"]

    # Tour de négo sur la conversation existante.
    second = await convex.mutation(
        "internal/chat:commitTurn",
        {
            "merchantId": merchant_id,
            "conversationId": conv_id,
            "clientPhone": client,
            "clientMessage": "Tu peux faire 22 000 ?",
            "botMessage": "Je peux faire 23 000 !",
            "newStatus": "negotiating",
            "currentOffer": 23000,
        },
    )
    assert second["created"] is False
    assert second["conversationId"] == conv_id

    ctx2 = await convex.query(
        "internal/chat:getContext",
        {"merchantPhone": DEMO_MERCHANT_PHONE, "clientPhone": client, "productCode": PRODUCT_CODE},
    )
    assert ctx2["conversation"]["status"] == "negotiating"
    assert ctx2["conversation"]["currentOffer"] == 23000
    assert len(ctx2["history"]) == 4  # 2 tours x 2 messages


async def test_committurn_replay_is_not_idempotent_but_safe(convex):
    """
    Idempotence d'un /incoming rejoué : rejouer le MÊME tour sur la conversation
    existante n'en recrée pas une nouvelle (created=False) — la conversation
    reste unique. (Les messages sont append-only, comportement attendu.)
    """
    client = _unique_client()
    ctx = await convex.query(
        "internal/chat:getContext",
        {"merchantPhone": DEMO_MERCHANT_PHONE, "clientPhone": client, "productCode": PRODUCT_CODE},
    )
    merchant_id = ctx["merchant"]["_id"]
    product_id = ctx["product"]["_id"]

    r1 = await convex.mutation(
        "internal/chat:commitTurn",
        {
            "merchantId": merchant_id,
            "productId": product_id,
            "clientPhone": client,
            "clientMessage": "Test rejeu",
            "botMessage": "OK",
            "newStatus": "active",
        },
    )
    conv_id = r1["conversationId"]

    # Rejeu : on réutilise la conversation, pas de nouvelle conversation créée.
    r2 = await convex.mutation(
        "internal/chat:commitTurn",
        {
            "merchantId": merchant_id,
            "conversationId": conv_id,
            "clientPhone": client,
            "clientMessage": "Test rejeu",
            "botMessage": "OK",
            "newStatus": "active",
        },
    )
    assert r2["created"] is False
    assert r2["conversationId"] == conv_id


async def test_schedule_followup_dedup_no_duplicate(convex):
    """
    Scheduler : deux planifications concurrentes pour la même conversation ne
    créent PAS deux relances pending (dédup atomique côté Convex — résout la
    race SELECT-puis-INSERT du followup_service.py SQLite).
    """
    client = _unique_client()
    ctx = await convex.query(
        "internal/chat:getContext",
        {"merchantPhone": DEMO_MERCHANT_PHONE, "clientPhone": client, "productCode": PRODUCT_CODE},
    )
    merchant_id = ctx["merchant"]["_id"]
    product_id = ctx["product"]["_id"]
    turn = await convex.mutation(
        "internal/chat:commitTurn",
        {
            "merchantId": merchant_id,
            "productId": product_id,
            "clientPhone": client,
            "clientMessage": "Je réfléchis",
            "botMessage": "Pas de souci !",
            "newStatus": "active",
        },
    )
    conv_id = turn["conversationId"]

    args = {
        "conversationId": conv_id,
        "merchantId": merchant_id,
        "merchantPhone": DEMO_MERCHANT_PHONE,
        "clientPhone": client,
        "productName": "Sneakers Blanches",
        "step": 1,
    }
    first = await convex.mutation("internal/followups:scheduleFollowup", dict(args))
    second = await convex.mutation("internal/followups:scheduleFollowup", dict(args))

    assert first["scheduled"] is True
    assert second["scheduled"] is False  # dédup : déjà pending
    assert second["reason"] == "already_pending"

    # Annulation propre (le client a « répondu »).
    cancelled = await convex.mutation(
        "internal/followups:cancelFollowups", {"conversationId": conv_id}
    )
    assert cancelled["cancelled"] == 1


# === Verrou /incoming (sécurité ingestion, indépendant de Convex) ===

async def test_incoming_internal_key_guard():
    """
    Le verrou `verify_internal_key` rejette les appels sans clé / mauvaise clé
    (401) et laisse passer la bonne clé. Garde le bridge <-> API server-to-server.
    """
    from fastapi import HTTPException
    from app.dependencies import verify_internal_key

    if not settings.internal_api_key:
        pytest.skip("INTERNAL_API_KEY non configurée — parité dev, garde désactivée.")

    with pytest.raises(HTTPException) as exc_none:
        await verify_internal_key(None)
    assert exc_none.value.status_code == 401

    with pytest.raises(HTTPException) as exc_bad:
        await verify_internal_key("mauvaise-cle")
    assert exc_bad.value.status_code == 401

    # Bonne clé : ne lève pas.
    await verify_internal_key(settings.internal_api_key)
