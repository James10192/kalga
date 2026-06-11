"""
Étage ⑤ — Filet de sortie (spec §9).

Scanne le texte AVANT envoi. Trois familles d'interdits :
1. Langage de clôture hors CONCLUSION/LOGISTIQUE (le « Banco ! » en texte libre
   de la capture 2 — désormais structurellement bloqué) ;
2. PROPOSITION d'un prix sous le plancher (citer l'offre basse du client reste
   permis : seul « je peux faire X » avec X < plancher est une violation) ;
3. Révélation du concept de prix minimum (le plancher reste secret).
"""
import re
from dataclasses import dataclass
from typing import List

from .actions import ActionPlan, ActionType
from .sale_state import SaleState

_DEAL_STATES = {SaleState.CONCLUSION, SaleState.LOGISTIQUE_LIVRAISON,
                SaleState.LOGISTIQUE_RETRAIT, SaleState.APRES_VENTE}

_CLOSING_PATTERNS = (
    "banco", "marché conclu", "marche conclu", "affaire conclue", "c'est vendu",
    "on s'entend pour", "on s'est entendu", "livraison ou", "tu passes chercher",
    "tu viens chercher ou", "on fait comment pour la livraison",
    "tu préfères la livraison", "tu preferes la livraison",
)
_SECRET_PATTERNS = ("prix minimum", "prix plancher", "mon minimum", "en dessous de mon prix")

# « je peux (te) faire 7 000 », « je descends à 7000 », « d'accord pour 7 000 »…
_PROPOSAL_RE = re.compile(
    r"(?:je peux (?:te |vous )?faire|je te fais|je descends? à|je te laisse à"
    r"|d'accord pour|ok pour|je propose)\s*([\d][\d\s.]{2,9})",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class GuardVerdict:
    ok: bool
    violations: List[str]


def guard_output(text: str, plan: ActionPlan, floor_price: float) -> GuardVerdict:
    low = (text or "").lower()
    violations: List[str] = []

    allows_close = (plan.new_state in _DEAL_STATES
                    or any(a.type == ActionType.CONFIRM_DEAL for a in plan.actions))
    if not allows_close and any(p in low for p in _CLOSING_PATTERNS):
        violations.append("cloture interdite hors conclusion")

    if any(p in low for p in _SECRET_PATTERNS):
        violations.append("secret du prix plancher révélé")

    for m in _PROPOSAL_RE.finditer(low):
        digits = re.sub(r"[\s.]", "", m.group(1))
        if digits.isdigit() and float(digits) < floor_price:
            violations.append(f"prix proposé {digits} sous le plancher")

    return GuardVerdict(ok=not violations, violations=violations)
