"""Tests des helpers de parsing du flux variantes en lot."""
from app.modules.merchant_commands.handlers.bulk_variant_creation import (
    parse_variant_list,
    parse_corrections,
    MAX_VARIANTS,
)


def test_parse_simple_list():
    assert parse_variant_list("rouge, bleu, noir") == ["rouge", "bleu", "noir"]


def test_parse_trims_and_drops_empty():
    assert parse_variant_list("rouge ,  , bleu ,") == ["rouge", "bleu"]


def test_parse_newlines_supported():
    assert parse_variant_list("rouge\nbleu\nnoir") == ["rouge", "bleu", "noir"]


def test_parse_dedupes_case_insensitive_keep_first():
    assert parse_variant_list("Rouge, rouge, ROUGE, bleu") == ["Rouge", "bleu"]


def test_parse_caps_at_max():
    items = ", ".join(f"c{i}" for i in range(MAX_VARIANTS + 5))
    assert len(parse_variant_list(items)) == MAX_VARIANTS


def test_parse_single_item_no_comma():
    assert parse_variant_list("rouge") == ["rouge"]


def test_corrections_ok_returns_empty():
    assert parse_corrections("ok", 3) == {}


def test_corrections_single():
    assert parse_corrections("3=beige", 3) == {3: "beige"}


def test_corrections_multiple():
    assert parse_corrections("3=beige, 1=bordeaux", 3) == {3: "beige", 1: "bordeaux"}


def test_corrections_ignores_out_of_range():
    assert parse_corrections("5=beige", 3) == {}


def test_corrections_unparseable_returns_empty():
    assert parse_corrections("n'importe quoi", 3) == {}
