"""
Configuration centralisée UNIQUE de l'application KALGA.
Toutes les settings sont ici — aucun autre fichier config.
"""
import sys

from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import Optional, List


class Settings(BaseSettings):
    """Configuration principale de l'application"""

    # === Application ===
    app_name: str = "KALGA API"
    app_version: str = "1.0.0"
    debug: bool = True
    environment: str = "development"

    # === API ===
    api_prefix: str = "/api"

    # === DeepSeek AI ===
    deepseek_api_key: Optional[str] = None
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-chat"
    deepseek_timeout: int = 30
    deepseek_max_retries: int = 3

    # === Moteur de dialogue (refonte 2026-06-11) ===
    # "v2" = pipeline dialogue/ (DÉFAUT depuis P5a) ; "v1" = ancien chemin (legacy,
    # retour arrière en une ligne d'env le temps de la période de validation)
    dialogue_engine: str = "v2"

    # === WhatsApp Bridge ===
    whatsapp_bridge_url: str = "http://localhost:3001"
    whatsapp_request_timeout: int = 10
    internal_api_key: str = ""

    # === Storefront ===
    storefront_base_url: str = "http://localhost:8001"

    # === CORS ===
    allowed_origins: List[str] = [
        "http://localhost:8001",
        "http://127.0.0.1:8001",
    ]

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

    # === JWT Authentication ===
    jwt_secret_key: str  # OBLIGATOIRE
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60 * 24
    jwt_refresh_token_expire_days: int = 30

    # === Admin ===
    admin_email: str = "admin@kalga.com"
    admin_password: str  # OBLIGATOIRE

    # === Trial ===
    trial_duration_days: int = 14
    trial_messages_limit: int = 500
    trial_products_limit: int = 10

    @field_validator("jwt_secret_key")
    @classmethod
    def jwt_secret_must_be_strong(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError(
                "JWT_SECRET_KEY doit faire au moins 32 caractères. "
                'Générez-en un avec: python -c "import secrets; print(secrets.token_hex(32))"'
            )
        return v

    @field_validator("admin_password")
    @classmethod
    def admin_password_must_be_strong(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("ADMIN_PASSWORD doit faire au moins 8 caractères.")
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# === Instanciation avec gestion d'erreur ===
try:
    settings = Settings()
except Exception as e:
    print("\n" + "=" * 60)
    print("ERREUR DE CONFIGURATION KALGA")
    print("=" * 60)
    print(f"  {e}")
    print("\nVérifiez votre fichier .env. Variables requises:")
    print("  JWT_SECRET_KEY=<au moins 32 caractères>")
    print("  ADMIN_PASSWORD=<au moins 8 caractères>")
    print("=" * 60 + "\n")
    sys.exit(1)


def get_settings() -> Settings:
    """Retourne l'instance singleton des settings"""
    return settings


def validate_settings() -> list[str]:
    """Vérifie les paramètres non-critiques au démarrage. Retourne les warnings."""
    warnings = []

    if not settings.deepseek_api_key:
        warnings.append(
            "DEEPSEEK_API_KEY non configurée! "
            "L'IA utilisera uniquement les réponses de fallback."
        )

    if not settings.internal_api_key:
        warnings.append(
            "INTERNAL_API_KEY non configurée! "
            "Le bridge WhatsApp ne sera pas protégé."
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
        print("AVERTISSEMENTS DE CONFIGURATION KALGA")
        print("=" * 60)
        for w in warnings:
            print(f"  - {w}")
        print("=" * 60 + "\n")


# Exécuter la validation au chargement du module
print_startup_warnings()
