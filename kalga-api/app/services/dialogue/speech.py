"""
Étage ④ — La parole (spec §9).

Le plan est DÉJÀ décidé. Ici on le met en mots :
- gabarits déterministes (render_fallback) — corrects, toujours disponibles ;
- LLM en habilleur (render) — plus naturel, vérifié par le filet,
  retombe sur les gabarits à la moindre violation ou indisponibilité.

La variété anti-boucle (hold_floor) est déterministe : round_seed (= nombre de
messages de la conversation) choisit la formulation — testable, sans hasard.
"""
from dataclasses import dataclass
from typing import Optional

from .actions import Action, ActionPlan, ActionType
from .output_guard import guard_output
from .llm_protocol import LLMClient


@dataclass
class SpeechContext:
    product_name: str
    listed_price: float
    floor_price: float
    round_seed: int = 0                 # varie les formulations (anti-boucle)
    persona: Optional[dict] = None      # bot_tone / bot_style / bot_catchphrase
    memory_block: Optional[str] = None  # contexte épisodique/LTM déjà formaté
    client_message: str = ""
    product_description: Optional[str] = None  # pour répondre aux questions produit


def _fmt(price: Optional[float]) -> str:
    return f"{int(price):,}".replace(",", " ") if price is not None else ""


_HOLD_FLOOR_VARIANTS = (
    "Je suis déjà à {p} F, c'est vraiment mon dernier prix 🙏",
    "{p} F c'est le prix final, je ne peux pas descendre plus bas !",
    "Crois-moi, à {p} F tu fais une bonne affaire — je ne bouge plus !",
)


def _action_text(action: Action, sctx: SpeechContext) -> str:
    t, facts = action.type, set(action.facts)
    p = _fmt(action.price)

    if t == ActionType.SEND_PHOTO:
        if "chosen_variant" in facts:
            label = f" {action.reason}" if action.reason else ""
            return f"Très bon choix !{label} 😍 Je te la remontre pour confirmer."
        return "C'est la seule photo que j'ai pour l'instant, la voilà ! 😊" \
            if "only_photo" in facts else "Voilà la photo ! 😊"
    if t == ActionType.SEND_VARIANTS:
        return "Je t'envoie les autres modèles disponibles 👇"
    if t == ActionType.SEND_LOCATION:
        return "Je t'envoie la localisation !"
    if t == ActionType.SEND_PAYMENT_INFO:
        return "Voici nos moyens de paiement :"
    if t == ActionType.COUNTER_OFFER:
        if "hold_floor" in facts:
            variant = _HOLD_FLOOR_VARIANTS[sctx.round_seed % len(_HOLD_FLOOR_VARIANTS)]
            return variant.format(p=p)
        return f"Je peux te faire {p} F, c'est un bon prix !"
    if t == ActionType.CONFIRM_DEAL:
        return f"C'est bon pour {p} F ! 🤝 Tu préfères la livraison ou tu passes chercher ?"
    if t == ActionType.REQUEST_ADDRESS:
        return "Parfait ! Donne-moi ton adresse de livraison ?"
    if t == ActionType.END_CONVERSATION:
        return "Pas de souci, reviens quand tu veux ! 😊"
    if t == ActionType.JOIN_WAITLIST:
        return "Réponds *OUI* pour rejoindre la liste prioritaire 🔔"
    if t == ActionType.HANDOVER_HUMAN:
        return "Je transmets au vendeur, il te répond très vite !"
    if t == ActionType.NOTIFY_MERCHANT:
        return ""  # action interne, pas de texte client

    # SEND_TEXT — selon les facts
    if "greeting" in facts:
        return (f"Salut ! 😊 Oui, le {sctx.product_name} est disponible "
                f"à {_fmt(sctx.listed_price)} F. Tu veux plus d'infos ?")
    if "price_ok_pending" in facts:
        return f"Pour {p} F c'est bon pour moi ! Dis-moi quand tu confirmes 👍"
    if "clarify_deal" in facts:
        return "On se met d'accord à combien ? Dis-moi ton prix 😊"
    if "apaisement" in facts:
        return "Désolé si je t'ai froissé, ce n'était pas le but 🙏"
    if "correction" in facts:
        return "Pardon pour la confusion ! Reformule ta question, je t'écoute."
    if "delivery_info" in facts:
        return "Pour les frais et délais de livraison, le vendeur te confirme ça vite !"
    if "catalogue" in facts:
        if "moins_cher" in facts:
            return "Bien sûr ! Voici ce qu'on a de plus abordable 👇"
        return "On a d'autres articles en boutique ! Dis-moi ce que tu cherches."
    if "out_of_stock" in facts:
        return f"Le {sctx.product_name} est momentanément épuisé 😕"
    if "address_confirmed" in facts:
        # Jamais de promesse d'horaire : c'est le VENDEUR qui organise.
        return "C'est noté ! Le vendeur te contacte très vite pour organiser la livraison 🚚"
    if "delivery_noted" in facts:
        return "Noté pour la livraison ! On règle d'abord le prix 😊"
    if "only_photo" in facts:
        return "C'est la seule photo que j'ai pour l'instant !"
    if any(f.startswith("info") for f in facts):
        if "info:prix" in facts:
            return f"Le {sctx.product_name} est à {_fmt(sctx.listed_price)} F."
        if "info:qualité" in facts:
            desc = f" {sctx.product_description}." if sctx.product_description else ""
            return f"Oui, c'est de la bonne qualité !{desc} Le vendeur le garantit 👍"
        if sctx.product_description:
            return f"Bonne question ! {sctx.product_description} 😊"
        return f"Bonne question ! Le {sctx.product_name} : je te confirme ça tout de suite."
    return "Je ne suis pas sûr d'avoir compris — tu peux préciser ? 😊"


def render_fallback(plan: ActionPlan, sctx: SpeechContext) -> str:
    """Gabarits déterministes : corrects, jamais indisponibles, jamais faux."""
    parts = [_action_text(a, sctx) for a in plan.actions]
    return " ".join(x for x in parts if x).strip()


def build_brief(plan: ActionPlan, sctx: SpeechContext) -> dict:
    """Brief verrouillé envoyé au LLM : la décision, les faits, les interdits."""
    forbidden = ["mentionner le prix minimum/plancher",
                 f"proposer un prix sous {int(sctx.floor_price)} F",
                 "promettre un horaire ou un délai de livraison "
                 "(c'est le vendeur qui organise et contacte le client)"]
    from .output_guard import _DEAL_STATES  # même définition que le filet
    if plan.new_state not in _DEAL_STATES:
        forbidden.append("conclure la vente ou parler de livraison/retrait")

    return {
        "actions": [
            {"type": a.type.value, "price": a.price, "facts": list(a.facts)}
            for a in plan.actions
        ],
        "state": plan.new_state.value,
        "product_name": sctx.product_name,
        "listed_price": sctx.listed_price,
        "client_message": sctx.client_message,
        "product_description": sctx.product_description,
        "persona": sctx.persona or {},
        "memory": sctx.memory_block,
        "forbidden": forbidden,
    }


async def render(plan: ActionPlan, sctx: SpeechContext,
                 llm: Optional[LLMClient]) -> str:
    """Rendu final : LLM contraint si disponible, gabarits sinon. Jamais faux."""
    if llm is None:
        return render_fallback(plan, sctx)

    brief = build_brief(plan, sctx)
    text = await llm.speak(brief)
    if text:
        verdict = guard_output(text, plan, sctx.floor_price)
        if verdict.ok:
            return text
        # Une seule reprise corrective, avec le motif
        retry_brief = dict(brief, violations=verdict.violations)
        text = await llm.speak(retry_brief)
        if text and guard_output(text, plan, sctx.floor_price).ok:
            return text

    return render_fallback(plan, sctx)
