from pydantic_settings import BaseSettings
from typing import Optional
import secrets


class Settings(BaseSettings):
    # API Configuration
    app_name: str = "KALGA API"
    debug: bool = True

    # DeepSeek API (pour les conversations IA)
    deepseek_api_key: Optional[str] = None
    deepseek_base_url: str = "https://api.deepseek.com/v1"

    # WhatsApp Bridge
    whatsapp_bridge_url: str = "http://localhost:3001"
    whatsapp_request_timeout: int = 10

    # Storefront (vitrine en ligne)
    storefront_base_url: str = "http://localhost:8001"

    # CORS — comma-separated list (e.g. "https://kalga.trycloudflare.com,http://localhost:8001")
    # Empty by default in prod (same-origin only). In debug, falls back to "*".
    allowed_origins: str = ""

    # Conversation settings
    conversation_expiry_days: int = 7

    # ============================================
    # AUTHENTIFICATION JWT
    # ============================================
    jwt_secret_key: str = secrets.token_hex(32)  # Généré si non fourni
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60 * 24  # 24 heures
    jwt_refresh_token_expire_days: int = 30

    # Admin par défaut (créé au premier lancement)
    admin_email: str = "admin@kalga.com"
    admin_password: str = "kalga2024!"  # À changer en production!

    # Trial settings
    trial_duration_days: int = 14
    trial_messages_limit: int = 500
    trial_products_limit: int = 10

    class Config:
        env_file = ".env"


settings = Settings()


# === VALIDATION AU DEMARRAGE ===
def validate_settings():
    """Vérifie les paramètres critiques au démarrage"""
    warnings = []

    if not settings.deepseek_api_key:
        warnings.append(
            "DEEPSEEK_API_KEY non configurée! "
            "L'IA utilisera uniquement les réponses de fallback."
        )

    if warnings:
        print("\n" + "=" * 60)
        print("⚠️  AVERTISSEMENTS DE CONFIGURATION KALGA")
        print("=" * 60)
        for w in warnings:
            print(f"  • {w}")
        print("=" * 60 + "\n")


# Exécuter la validation au chargement du module
validate_settings()
