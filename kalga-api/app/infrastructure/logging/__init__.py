"""
Configuration du logging structuré pour KALGA
"""
import os
import logging
import glob
from datetime import datetime, timedelta
from pathlib import Path

from ...core.config import settings


# Dossier des logs
LOGS_DIR = Path(__file__).parent.parent.parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)


def get_log_filename(log_type: str = "api") -> str:
    """Retourne le nom du fichier de log du jour"""
    today = datetime.now().strftime("%Y-%m-%d")
    return str(LOGS_DIR / f"{log_type}-{today}.log")


def setup_logging() -> logging.Logger:
    """Configure le système de logging"""
    # Format enrichi
    log_format = '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'

    # Logger principal
    logger = logging.getLogger("kalga")
    logger.setLevel(logging.DEBUG if settings.debug else logging.INFO)

    # Éviter les doublons si déjà configuré
    if logger.handlers:
        return logger

    # Handler fichier principal (INFO+)
    file_handler = logging.FileHandler(
        get_log_filename("api"),
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(log_format, date_format))

    # Handler fichier erreurs (ERROR+)
    error_handler = logging.FileHandler(
        get_log_filename("errors"),
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(logging.Formatter(log_format, date_format))

    # Handler console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if settings.debug else logging.INFO)
    console_handler.setFormatter(logging.Formatter(log_format, date_format))

    # Ajouter les handlers
    logger.addHandler(file_handler)
    logger.addHandler(error_handler)
    logger.addHandler(console_handler)

    return logger


def cleanup_old_logs(days: int = 7) -> int:
    """
    Supprime les fichiers de log de plus de X jours.
    Retourne le nombre de fichiers supprimés.
    """
    cutoff = datetime.now() - timedelta(days=days)
    deleted = 0

    for pattern in ["api-*.log", "errors-*.log"]:
        for log_file in glob.glob(str(LOGS_DIR / pattern)):
            try:
                basename = os.path.basename(log_file)
                date_str = basename.split("-", 1)[1].replace(".log", "")
                file_date = datetime.strptime(date_str, "%Y-%m-%d")
                if file_date < cutoff:
                    os.remove(log_file)
                    deleted += 1
            except (ValueError, OSError):
                pass

    return deleted


def get_logger(name: str) -> logging.Logger:
    """Retourne un logger avec le préfixe kalga"""
    return logging.getLogger(f"kalga.{name}")


# Initialiser le logging au chargement du module
logger = setup_logging()
cleanup_old_logs()

__all__ = [
    "setup_logging",
    "get_log_filename",
    "cleanup_old_logs",
    "get_logger",
    "logger",
    "LOGS_DIR",
]
