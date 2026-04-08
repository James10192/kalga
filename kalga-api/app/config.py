import sys

from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import Optional, List


class Settings(BaseSettings):
    # API Configuration
    app_name: str = "KALGA API"
    debug: bool = True

    # DeepSeek API (pour les conversations IA)
    deepseek_api_key: Optional[str] = None
    deepseek_base_url: str = "https://api.deepseek.com/v1"

    # WhatsApp Bridge
    whatsapp_bridge_url: str = "http://localhost:3001"

    # Storefront (vitrine en ligne)
    storefront_base_url: str = "http://localhost:8001"

    # CORS — origines autorisées (séparées par virgule dans .env)
    allowed_origins: List[str] = [
        "http://localhost:8001",
        "http://127.0.0.1:8001",
    ]

    # Conversation settings
    conversation_expiry_days: int = 7

    # ============================================
    # AUTHENTIFICATION JWT
    # ============================================
    jwt_secret_key: str  # OBLIGATOIRE — pas de valeur par défaut
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60 * 24  # 24 heures
    jwt_refresh_token_expire_days: int = 30

    # Admin par défaut (créé au premier lancement)
    admin_email: str = "admin@kalga.com"
    admin_password: str  # OBLIGATOIRE — pas de valeur par défaut

    # Clé interne pour le bridge WhatsApp
    internal_api_key: str = ""

    # Trial settings
    trial_duration_days: int = 14
    trial_messages_limit: int = 500
    trial_products_limit: int = 10

    @field_validator("jwt_secret_key")
    @classmethod
    def jwt_secret_must_be_strong(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError(
                "JWT_SECRET_KEY doit faire au moins 32 caractères. "
                "Générez-en un avec: python -c \"import secrets; print(secrets.token_hex(32))\""
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


# === VALIDATION AU DEMARRAGE ===
def validate_settings():
    """Vérifie les paramètres non-critiques au démarrage"""
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

    if warnings:
        print("\n" + "=" * 60)
        print("AVERTISSEMENTS DE CONFIGURATION KALGA")
        print("=" * 60)
        for w in warnings:
            print(f"  - {w}")
        print("=" * 60 + "\n")


# Exécuter la validation au chargement du module
validate_settings()
