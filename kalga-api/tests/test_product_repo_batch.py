"""Tests de ProductRepository.create_variants_batch."""
import pytest

from app.database.repositories.product_repo import ProductRepository
from app.database.connection import get_connection


async def _make_merchant_and_base(repo):
    async with get_connection() as db:
        cur = await db.execute(
            "INSERT INTO merchants (name, phone) VALUES (?, ?)",
            ("Test", "2250700000000"),
        )
        await db.commit()
        merchant_id = cur.lastrowid
    base = await repo.create(
        merchant_id=merchant_id, name="Sac", price=15000, min_price=12000,
        description="Joli sac", group_id="GRP-TEST01",
    )
    return merchant_id, base


async def test_batch_creates_all_variants(temp_db):
    repo = ProductRepository()
    merchant_id, base = await _make_merchant_and_base(repo)
    created = await repo.create_variants_batch(
        merchant_id=merchant_id, base_name="Sac", price=15000, min_price=12000,
        description="Joli sac", group_id="GRP-TEST01",
        variants=[
            {"variant_name": "Rouge", "image_path": None},
            {"variant_name": "Bleu", "image_path": "b.jpg"},
            {"variant_name": "Noir", "image_path": None},
        ],
    )
    assert len(created) == 3


async def test_batch_shares_group_and_price(temp_db):
    repo = ProductRepository()
    merchant_id, base = await _make_merchant_and_base(repo)
    created = await repo.create_variants_batch(
        merchant_id=merchant_id, base_name="Sac", price=15000, min_price=12000,
        description=None, group_id="GRP-TEST01",
        variants=[{"variant_name": "Rouge", "image_path": None}],
    )
    v = created[0]
    assert v["group_id"] == "GRP-TEST01"
    assert v["price"] == 15000
    assert v["variant_name"] == "Rouge"
    assert v["name"] == "Sac - Rouge"


async def test_batch_codes_are_sequential_and_unique(temp_db):
    repo = ProductRepository()
    merchant_id, base = await _make_merchant_and_base(repo)
    created = await repo.create_variants_batch(
        merchant_id=merchant_id, base_name="Sac", price=15000, min_price=12000,
        description=None, group_id="GRP-TEST01",
        variants=[
            {"variant_name": "Rouge", "image_path": None},
            {"variant_name": "Bleu", "image_path": None},
        ],
    )
    codes = [v["code"] for v in created]
    assert len(set(codes)) == 2
    nums = sorted(int(c[2:]) for c in codes)
    assert nums[1] == nums[0] + 1


async def test_batch_rolls_back_on_failure(temp_db):
    """Un variant_name None viole NOT NULL → aucune variante ne doit être créée."""
    repo = ProductRepository()
    merchant_id, base = await _make_merchant_and_base(repo)
    before = await repo.get_by_merchant(merchant_id)
    with pytest.raises(Exception):
        await repo.create_variants_batch(
            merchant_id=merchant_id, base_name="Sac", price=15000, min_price=12000,
            description=None, group_id="GRP-TEST01",
            variants=[
                {"variant_name": "Rouge", "image_path": None},
                {"variant_name": None, "image_path": None},  # invalide
            ],
        )
    after = await repo.get_by_merchant(merchant_id)
    assert len(after) == len(before)  # rollback : rien d'ajouté


async def test_batch_empty_list_raises(temp_db):
    """Un lot vide doit lever ValueError (évite un SELECT ... IN () invalide)."""
    repo = ProductRepository()
    merchant_id, base = await _make_merchant_and_base(repo)
    with pytest.raises(ValueError):
        await repo.create_variants_batch(
            merchant_id=merchant_id, base_name="Sac", price=15000, min_price=12000,
            description=None, group_id="GRP-TEST01", variants=[],
        )
