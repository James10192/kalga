"""
Configuration centralisée de l'application KALGA
Utilise Pydantic Settings pour la validation et le chargement des variables d'environnement
"""
from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Configuration principale de l'application"""

    # === Application ===
    app_name: str = "KALGA API"
    app_version: str = "1.0.0"
    debug: bool = True
    environment: str = "development"  # development, staging, production

    # === API ===
    api_prefix: str = "/api"

    # === DeepSeek AI ===
    deepseek_api_key: Optional[str] = None
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-chat"
    deepseek_timeout: int = 30
    deepseek_max_retries: int = 3

    # === WhatsApp Bridge ===
    whatsapp_bridge_url: str = "http://localhost:3001"
    whatsapp_request_timeout: int = 10

    # === Database ===
    database_path: str = "kalga.db"

    # === Sessions ===
    session_timeout_minutes: int = 10
    conversation_expiry_days: int = 7

    # === Rate Limiting ===
    rate_limit_requests: int = 30
    rate_limit_period: str = "minute"

    # === Logging ===
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Retourne une instance singleton des settings"""
    return Settings()


# Instance globale pour accès rapide
settings = get_settings()


def validate_settings() -> list[str]:
    """
    Vérifie les paramètres critiques au démarrage.
    Retourne la liste des avertissements.
    """
    warnings = []

    if not settings.deepseek_api_key:
        warnings.append(
            "DEEPSEEK_API_KEY non configurée! "
            "L'IA utilisera uniquement les réponses de fallback."
        )

    if settings.environment == "production" and settings.debug:
        warnings.append(
            "Mode DEBUG activé en production! "
            "Désactivez DEBUG pour la production."
        )

    return warnings


def print_startup_warnings():
    """Affiche les avertissements de configuration au démarrage"""
    warnings = validate_settings()

    if warnings:
        print("\n" + "=" * 60)
        print("⚠️  AVERTISSEMENTS DE CONFIGURATION KALGA")
        print("=" * 60)
        for w in warnings:
            print(f"  • {w}")
        print("=" * 60 + "\n")
