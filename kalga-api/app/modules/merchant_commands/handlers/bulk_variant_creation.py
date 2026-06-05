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


def _read_upload_bytes(image_path: str) -> Optional[bytes]:
    """Lit les bytes d'une image stockée dans le dossier uploads."""
    if not image_path:
        return None
    full = os.path.join(_UPLOADS_DIR, image_path)
    try:
        with open(full, "rb") as f:
            return f.read()
    except OSError as e:
        logger.debug(f"_read_upload_bytes: {e}")
        return None


class BulkVariantCreationHandler(BaseHandler):
    """Gère les flux de création de variantes en lot."""

    async def handle(
        self,
        session: ProductSession,
        message: str,
        image_path: Optional[str],
        db: Any,
    ) -> CommandResponse:
        step = session.step
        if step == CreationStep.VARIANT_BATCH_PHOTOS:
            return await self._handle_batch_photos(session, message, image_path, db)
        if step == CreationStep.VARIANT_BATCH_CONFIRM:
            return await self._handle_batch_confirm(session, message, db)
        logger.warning(f"Étape non gérée par BulkVariantCreationHandler: {step}")
        return self._error("Erreur interne: étape non reconnue")

    async def _handle_batch_photos(
        self, session, message, image_path, db
    ) -> CommandResponse:
        """Bufferise les photos ; 'fini' → récap de validation."""
        if image_path:
            from ....services.ai.color_detection import detect_color
            img_bytes = _read_upload_bytes(image_path)
            guess = detect_color(img_bytes) if img_bytes else None
            buffer = session.get_data("batch_photos") or []
            buffer.append({
                "image_path": image_path,
                "name": guess.name if guess else "à préciser",
                "confidence": guess.confidence if guess else 0.0,
            })
            session.set_data("batch_photos", buffer)
            if len(buffer) == 1:
                return self._response(
                    "📸 Photo reçue ! Envoie les autres, puis écris *fini*.",
                    CommandAction.VARIANT_BATCH_STEP,
                )
            return self._ignored()  # silence anti-ban sur les suivantes

        if message.strip().lower() in ("fini", "termine", "terminé", "ok", "stop"):
            buffer = session.get_data("batch_photos") or []
            if not buffer:
                return self._response(
                    "Je n'ai encore reçu aucune photo. Envoie-les puis écris *fini*.",
                    CommandAction.ASK_AGAIN,
                )
            pending = [
                {"variant_name": item["name"], "image_path": item["image_path"]}
                for item in buffer
            ]
            session.set_data("pending_variants", pending)
            session.update_step(CreationStep.VARIANT_BATCH_CONFIRM)
            return self._response(self._build_recap(buffer),
                                  CommandAction.VARIANT_BATCH_STEP)

        return self._response(
            "Envoie tes photos une par une, puis écris *fini*.",
            CommandAction.ASK_AGAIN,
        )

    def _build_recap(self, buffer: List[Dict]) -> str:
        lines = ["J'ai reçu ces photos, voici les noms détectés :", ""]
        for i, item in enumerate(buffer, start=1):
            mark = "✅" if item["confidence"] >= 0.6 else "⚠️"
            lines.append(f"{i}. {item['name']}  {mark}")
        lines.append("")
        lines.append('→ Réponds *ok* pour créer, ou corrige : ex. "2=beige, 1=bordeaux"')
        return "\n".join(lines)

    async def _handle_batch_confirm(self, session, message, db) -> CommandResponse:
        """Applique les corrections puis crée les variantes."""
        pending = session.get_data("pending_variants") or []
        if not pending:
            session_manager.delete(session.merchant_phone)
            return self._error("Aucune variante en attente. Recommence avec *variantes #code*.")

        corrections = parse_corrections(message, len(pending))
        cleaned = message.strip().lower()
        is_accept = cleaned in ("ok", "oui", "valider", "valide", "c'est bon", "cest bon")
        if not corrections and not is_accept:
            return self._response(
                'Réponds *ok* pour valider, ou corrige : ex. "2=beige".',
                CommandAction.ASK_AGAIN,
            )
        for idx, name in corrections.items():
            pending[idx - 1]["variant_name"] = name

        # Refus de création si une variante reste "à préciser"
        unresolved = [i + 1 for i, v in enumerate(pending)
                      if v["variant_name"] == "à préciser"]
        if unresolved:
            nums = ", ".join(str(n) for n in unresolved)
            return self._response(
                f"Nomme d'abord : {nums}. Ex. \"{unresolved[0]}=rouge\".",
                CommandAction.ASK_AGAIN,
            )

        from ....database.repositories.product_repo import ProductRepository
        repo = ProductRepository()
        try:
            created = await repo.create_variants_batch(
                merchant_id=session.get_data("merchant_id"),
                base_name=session.get_data("name"),
                price=session.get_data("price"),
                min_price=session.get_data("min_price"),
                description=session.get_data("description"),
                group_id=session.get_data("group_id"),
                variants=pending,
            )
        except Exception as e:
            logger.error(f"Échec création variantes en lot: {e}")
            session_manager.delete(session.merchant_phone)
            return self._error("Erreur lors de la création des variantes. Réessaie.")

        original_code = session.get_data("original_code")
        session_manager.delete(session.merchant_phone)
        lines = [f"✅ *{len(created)} variantes créées !*", ""]
        for v in created:
            lines.append(f"• {v['variant_name']} ({v['code']})")
        lines.append("")
        lines.append(f"👉 Ajoute *{original_code}* dans ton Status WhatsApp.")
        return self._response("\n".join(lines), CommandAction.VARIANTS_BATCH_CREATED,
                              product_code=original_code)
