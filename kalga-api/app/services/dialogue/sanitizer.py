"""
Étage ① — Sas d'entrée.

Les messages bruts portent des préfixes de contexte ajoutés par le bridge ou le
système, qui contiennent des mots déclencheurs n'appartenant pas au client :
    [Répond à la photo: "#K053"] Hello        (réponse à un Statut/image)
    [Répond à: "..."] texte                    (réponse à un message)
    [🎤 Vocal transcrit (fr)]: texte           (note vocale transcrite)
    [📸 Recherche visuelle — ...]              (instruction système, sans texte client)

Aucun détecteur en aval ne doit jamais voir ces blocs : seuls les mots
réellement tapés (ou dits) par le client comptent.
"""
import re
from typing import Optional

_CONTEXT_PREFIX_RE = re.compile(r"^\s*\[[^\]]*\]:?\s*")
_MOBILE_APOSTROPHES = {"’": "'", "‘": "'"}
_WHITESPACE_RE = re.compile(r"\s+")

# Le préfixe « réponse à une photo » n'est pas un déchet : il porte le CHOIX du
# client (à quelle image il répond). On l'extrait AVANT de nettoyer.
# Format bridge : [Répond à la photo: "Modèle Fleur"] message
_REPLY_PHOTO_RE = re.compile(r'^\s*\[Répond à la photo:\s*"([^"]+)"\]')


def get_replied_photo_label(message) -> Optional[str]:
    """Légende de la photo à laquelle le client répond, si le message est une
    réponse à une image (variante choisie, Statut…). None sinon."""
    m = _REPLY_PHOTO_RE.match(message or "")
    return m.group(1).strip() if m else None


def strip_context_prefix(message) -> str:
    """Retire tous les blocs [contexte] en tête de message.

    Un message 100 % système (uniquement des blocs) devient "" — les règles ne
    s'appliquent alors pas et l'appelant garde la main (LLM ou flux normal).
    """
    msg = message or ""
    while True:
        stripped = _CONTEXT_PREFIX_RE.sub("", msg, count=1)
        if stripped == msg:
            return msg
        msg = stripped


def normalize(message) -> str:
    """Texte client canonique : sans préfixes, apostrophes droites, espaces propres."""
    msg = strip_context_prefix(message)
    for bad, good in _MOBILE_APOSTROPHES.items():
        msg = msg.replace(bad, good)
    return _WHITESPACE_RE.sub(" ", msg).strip()
