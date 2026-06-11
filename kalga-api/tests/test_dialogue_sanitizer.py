"""Tests du sanitizer — étage ① du pipeline de dialogue.

Les messages arrivent du bridge avec des préfixes de contexte qui contiennent
des mots déclencheurs (« photo »…) n'appartenant PAS au client. Bug terrain :
« hello » sur un Statut arrivait comme [Répond à la photo: "#K053"] Hello.
"""
from app.services.dialogue.sanitizer import strip_context_prefix, normalize


def test_strip_bridge_reply_prefix():
    assert strip_context_prefix('[Répond à la photo: "#K053"] Hello') == "Hello"


def test_strip_voice_prefix_with_colon():
    assert strip_context_prefix("[🎤 Vocal transcrit (fr)]: je veux la photo") == "je veux la photo"


def test_strip_multiple_prefixes():
    assert strip_context_prefix('[Répond à: "ok"] [🎤 Vocal transcrit (fr)]: oui') == "oui"


def test_bracket_only_system_message_becomes_empty():
    # Message 100 % système (ex. instruction de recherche visuelle) → ""
    assert strip_context_prefix("[📸 Le client a envoyé une photo. Présente-lui les produits.]") == ""


def test_plain_message_untouched():
    assert strip_context_prefix("je veux la photo") == "je veux la photo"


def test_none_and_empty_are_safe():
    assert strip_context_prefix(None) == ""
    assert strip_context_prefix("") == ""


def test_normalize_mobile_apostrophes():
    # iOS/Android génèrent ’ au lieu de '
    assert normalize("d’autres couleurs") == "d'autres couleurs"


def test_normalize_collapses_whitespace_and_strips():
    assert normalize("  je   veux\n ça  ") == "je veux ça"


def test_normalize_strips_context_prefix_first():
    assert normalize('[Répond à la photo: "#K053"]   Hello  ') == "Hello"
