"""
Shim de compatibilité — la config réelle est dans app.core.config.
Ce fichier sera supprimé une fois tous les imports migrés.
"""
from app.core.config import settings, Settings, validate_settings, get_settings

__all__ = ["settings", "Settings", "validate_settings", "get_settings"]
