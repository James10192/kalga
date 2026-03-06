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
import subprocess
import tempfile
from typing import Optional

logger = logging.getLogger("kalga.tts")

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
