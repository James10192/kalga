"""
Service de transcription audio via faster-whisper.
Chargement lazy du modèle (au 1er appel) pour ne pas bloquer le démarrage.
"""
import asyncio
import logging
import tempfile
from pathlib import Path
from typing import Tuple

logger = logging.getLogger("kalga.transcription")

_model = None  # Singleton chargé au 1er appel


def _get_model():
    global _model
    if _model is None:
        try:
            from faster_whisper import WhisperModel
            # 'small' : meilleur ratio vitesse/qualité sur CPU pour fr/ar
            _model = WhisperModel("small", device="cpu", compute_type="int8")
            logger.info("faster-whisper model 'small' chargé")
        except ImportError:
            logger.warning("faster-whisper non installé — transcription indisponible")
            return None
    return _model


def _transcribe_sync(audio_bytes: bytes) -> Tuple[str, str]:
    """Exécuté dans un thread pool (bloquant)."""
    model = _get_model()
    if model is None:
        return "", "unknown"

    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
        f.write(audio_bytes)
        tmp_path = f.name

    try:
        segments, info = model.transcribe(
            tmp_path,
            beam_size=5,
            language=None,   # auto-détection
            vad_filter=True, # filtre les silences
        )
        text = " ".join(seg.text.strip() for seg in segments)
        return text.strip(), info.language
    finally:
        Path(tmp_path).unlink(missing_ok=True)


async def transcribe_voice_note(audio_bytes: bytes) -> Tuple[str, str]:
    """
    Transcrit une note vocale OGG/Opus.
    Retourne (texte_transcrit, langue_détectée).
    Exécuté en thread pool pour ne pas bloquer l'event loop FastAPI.
    """
    loop = asyncio.get_running_loop()
    text, language = await loop.run_in_executor(None, _transcribe_sync, audio_bytes)
    logger.info("Transcription terminée", extra={"lang": language, "chars": len(text)})
    return text, language
