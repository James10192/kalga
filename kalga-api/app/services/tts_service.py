"""
Service TTS (Text-to-Speech) pour KALGA.
Génère des notes vocales OGG/Opus à partir de texte via Microsoft Edge TTS.

Pipeline: texte → edge-tts (MP3 en mémoire) → ffmpeg imageio (OGG/Opus)
Pas de dépendance système : imageio-ffmpeg embarque son propre binaire ffmpeg.

Voix supportées :
  - fr : fr-FR-DeniseNeural (voix naturelle féminine, claire)
  - ar : ar-MA-JamalNeural  (arabe marocain masculin)
  - en : en-US-JennyNeural
"""
import asyncio
import logging
import os
import re
import subprocess
import tempfile
from typing import Optional

logger = logging.getLogger("kalga.tts")

# Émojis et symboles que la voix ne doit JAMAIS lire (terrain : le client
# entendait « visage souriant », « fraise » au milieu des phrases).
_EMOJI_RE = re.compile(
    "["
    "\U0001F000-\U0001FAFF"   # émojis, symboles, pictogrammes (incl. 🤝 🍓 🌹)
    "\U00002600-\U000027BF"   # divers symboles + dingbats (☀ ✅ ✊ ➡)
    "\U00002B00-\U00002BFF"   # flèches et symboles divers
    "\U0001F1E6-\U0001F1FF"   # drapeaux
    "\U0000FE0F\U0000200D"    # sélecteurs de variante + ZWJ
    "\U00002190-\U000021FF"   # flèches
    "]+"
)
_MARKDOWN_RE = re.compile(r"[*_~`]")
_PRODUCT_CODE_RE = re.compile(r"#K(\d+)", re.IGNORECASE)


def clean_for_speech(text: str) -> str:
    """Prépare un texte pour la synthèse vocale : sans émojis, sans Markdown,
    codes produit prononçables. Ne touche ni aux accents ni à la ponctuation."""
    cleaned = _EMOJI_RE.sub(" ", text or "")
    cleaned = _MARKDOWN_RE.sub("", cleaned)
    cleaned = _PRODUCT_CODE_RE.sub(r"code K \1", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    # Espace orphelin avant , . ; : (la typographie française GARDE l'espace
    # avant ! et ? — on n'y touche pas)
    cleaned = re.sub(r"\s+([.,;:])", r"\1", cleaned)
    return cleaned

# Mapping langue → voix Edge TTS
_VOICE_MAP = {
    "fr": "fr-FR-DeniseNeural",
    "ar": "ar-MA-JamalNeural",
    "en": "en-US-JennyNeural",
}
_DEFAULT_VOICE = "fr-FR-DeniseNeural"


def _get_ffmpeg() -> Optional[str]:
    """Retourne le chemin vers ffmpeg (imageio-ffmpeg ou système)."""
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        pass
    import shutil
    return shutil.which("ffmpeg")


def _mp3_to_ogg_sync(mp3_bytes: bytes) -> Optional[bytes]:
    """
    Convertit des bytes MP3 → OGG/Opus via ffmpeg.
    Retourne None si ffmpeg est indisponible ou si la conversion échoue.
    """
    ffmpeg = _get_ffmpeg()
    if not ffmpeg:
        logger.error("ffmpeg introuvable — TTS vocal indisponible (retour texte)")
        return None

    tmp_mp3 = None
    tmp_ogg = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(mp3_bytes)
            tmp_mp3 = f.name
        tmp_ogg = tmp_mp3.replace(".mp3", ".ogg")

        result = subprocess.run(
            [
                ffmpeg, "-y",
                "-i", tmp_mp3,
                "-c:a", "libopus",
                "-b:a", "32k",
                "-ar", "16000",
                "-ac", "1",
                "-f", "ogg",
                tmp_ogg,
            ],
            capture_output=True,
            timeout=30,
        )
        if result.returncode != 0:
            logger.error("ffmpeg conversion failed: %s", result.stderr.decode()[-300:])
            return None

        with open(tmp_ogg, "rb") as f:
            return f.read()

    except Exception as e:
        logger.error("Erreur conversion MP3->OGG: %s", e)
        return None
    finally:
        for path in (tmp_mp3, tmp_ogg):
            if path and os.path.exists(path):
                try:
                    os.unlink(path)
                except OSError:
                    pass


async def text_to_ogg(text: str, lang: str = "fr") -> Optional[bytes]:
    """
    Convertit un texte en OGG/Opus (format PTT WhatsApp).

    Args:
        text: Texte a synthetiser (max ~500 chars conseille pour le naturel)
        lang: Code langue ('fr', 'ar', 'en'). Defaut: 'fr'.

    Returns:
        bytes OGG/Opus si succes, None si edge-tts ou ffmpeg indisponible.
    """
    try:
        import edge_tts
    except ImportError:
        logger.warning("edge-tts non installe — TTS indisponible")
        return None

    text = clean_for_speech(text)
    if not text:
        logger.debug("TTS: texte vide après nettoyage, pas de vocal")
        return None

    voice = _VOICE_MAP.get(lang, _DEFAULT_VOICE)

    try:
        tts = edge_tts.Communicate(text, voice=voice)
        mp3_chunks = []
        async for chunk in tts.stream():
            if chunk["type"] == "audio":
                mp3_chunks.append(chunk["data"])

        if not mp3_chunks:
            logger.warning("edge-tts: aucun audio genere")
            return None

        mp3_bytes = b"".join(mp3_chunks)
        logger.debug("edge-tts MP3: %d bytes, voix=%s", len(mp3_bytes), voice)

        loop = asyncio.get_running_loop()
        ogg_bytes = await loop.run_in_executor(None, _mp3_to_ogg_sync, mp3_bytes)

        if ogg_bytes:
            logger.info(
                "TTS OGG genere: %d bytes (lang=%s, voix=%s)",
                len(ogg_bytes), lang, voice,
            )
        return ogg_bytes

    except Exception as e:
        logger.error("Erreur TTS: %s", e)
        return None
