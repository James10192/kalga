"""
Bug terrain n°12 (2026-06-11 17:30) : la synthèse vocale lisait les émojis
à voix haute — le client entendait « visage souriant », « fraise », « banane »
au milieu des phrases. Le texte doit être nettoyé avant de parler.
"""
from app.services.tts_service import clean_for_speech


def test_emojis_are_stripped():
    text = "Voici la photo des fruits pour dessert 🍓🍌. Dis-moi 😊"
    cleaned = clean_for_speech(text)
    assert "🍓" not in cleaned and "🍌" not in cleaned and "😊" not in cleaned
    assert "Voici la photo des fruits pour dessert" in cleaned
    assert "Dis-moi" in cleaned


def test_symbols_and_markdown_are_stripped():
    assert clean_for_speech("C'est bon pour *19 000 F* ! 🤝") == "C'est bon pour 19 000 F !"


def test_product_code_is_spoken_naturally():
    cleaned = clean_for_speech("Le code est #K057")
    assert "#" not in cleaned
    assert "code K 057" in cleaned


def test_french_accents_preserved():
    assert clean_for_speech("Très bonne qualité, livré chez toi ✅") \
        == "Très bonne qualité, livré chez toi"


def test_whitespace_collapsed():
    assert clean_for_speech("Salut  🌹  ça va ?") == "Salut ça va ?"


def test_empty_after_clean():
    assert clean_for_speech("🤝🙏😊") == ""
