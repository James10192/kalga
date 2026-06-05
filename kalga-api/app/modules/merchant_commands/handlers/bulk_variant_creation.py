"""
Handler de création de variantes EN LOT.

Deux flux :
- Mode liste texte : "rouge, bleu, noir" → création immédiate (tout type de variante).
- Mode lot de photos : photos bufferisées → détection couleur (suggestion) →
  validation/correction → création.

La détection couleur n'est qu'une suggestion ; le marchand valide toujours.
"""
from typing import Optional, Any, Dict, List
import os
import re
import logging

from .base import BaseHandler
from ..session_manager import ProductSession, session_manager
from ..schemas import CommandResponse, CommandAction, CreationStep

logger = logging.getLogger("kalga.handlers.bulk_variant")

MAX_VARIANTS = 30

# Dossier des images uploadées (cohérent avec routers/products.py et main.py).
_UPLOADS_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "..", "uploads"
)


def parse_variant_list(text: str) -> List[str]:
    """
    Découpe une liste de noms de variantes sur virgules / retours à la ligne.
    Trim, supprime les vides, dédoublonne (insensible à la casse, garde la 1ʳᵉ
    occurrence), plafonne à MAX_VARIANTS.
    """
    raw = re.split(r"[,\n]+", text)
    result: List[str] = []
    seen = set()
    for item in raw:
        name = item.strip()
        if not name:
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(name)
        if len(result) >= MAX_VARIANTS:
            break
    return result


def parse_corrections(text: str, n: int) -> Dict[int, str]:
    """
    Parse des corrections du type "3=beige, 1=bordeaux".
    "ok"/"oui"/"valider" → {} (on accepte les suggestions).
    Indices hors plage [1..n] ignorés. Aucun motif valide → {}.
    """
    cleaned = text.strip().lower()
    if cleaned in ("ok", "oui", "valider", "valide", "c'est bon", "cest bon"):
        return {}
    corrections: Dict[int, str] = {}
    for match in re.finditer(r"(\d+)\s*=\s*([^,;\n]+)", text):
        idx = int(match.group(1))
        name = match.group(2).strip()
        if 1 <= idx <= n and name:
            corrections[idx] = name
    return corrections
