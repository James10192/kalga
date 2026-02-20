"""
Événements de cycle de vie de l'application FastAPI
Gère le démarrage et l'arrêt propre de l'application
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
import logging

from .config import settings, print_startup_warnings
from ..database import get_db

logger = logging.getLogger("kalga.events")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gère le cycle de vie de l'application.
    - Startup: Initialisation DB, validation config, logging
    - Shutdown: Nettoyage des ressources
    """
    # === STARTUP ===
    logger.info("=" * 50)
    logger.info(f"🚀 Démarrage {settings.app_name} v{settings.app_version}")
    logger.info(f"   Environnement: {settings.environment}")
    logger.info(f"   Debug: {settings.debug}")
    logger.info("=" * 50)

    # Afficher les avertissements de configuration
    print_startup_warnings()

    # Initialiser la base de données
    try:
        db = await get_db()
        logger.info("✅ Base de données initialisée")
    except Exception as e:
        logger.error(f"❌ Erreur initialisation DB: {e}")
        raise

    # Vérifier la connexion au bridge WhatsApp (non bloquant)
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.whatsapp_bridge_url}/health",
                timeout=5.0
            )
            if response.status_code == 200:
                logger.info("✅ WhatsApp Bridge accessible")
            else:
                logger.warning("⚠️ WhatsApp Bridge répond mais statut non-OK")
    except Exception as e:
        logger.warning(f"⚠️ WhatsApp Bridge non accessible: {e}")

    logger.info("🟢 Application prête à recevoir des requêtes")

    yield  # L'application tourne ici

    # === SHUTDOWN ===
    logger.info("🔴 Arrêt de l'application...")

    # Nettoyer les sessions de création en cours
    try:
        from ..modules.merchant_commands import session_manager
        active_sessions = session_manager.get_active_count()
        if active_sessions > 0:
            logger.info(f"   Nettoyage de {active_sessions} sessions actives")
            session_manager.clear_all()
    except ImportError:
        pass  # Module pas encore créé ou pas utilisé

    logger.info("👋 Application arrêtée proprement")
