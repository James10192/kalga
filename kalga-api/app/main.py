from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import os
import logging
from datetime import datetime

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .config import settings
from .rate_limiter import limiter
from .database import get_db
from .routers import merchants_router, products_router, chat_router, merchant_commands_router
from .routers.stats import router as stats_router
from .routers.categories import router as categories_router
from .routers.import_export import router as import_export_router
from .routers.away_mode import router as away_mode_router
from .routers.auth import router as auth_router
from .routers.admin import router as admin_router
from .routers.activation import router as activation_router
from .routers.storefront import router as storefront_router
from .services.followup_service import get_followup_service
from .database.repositories.user_repo import get_user_repository

# ========== SYSTÈME DE LOGS AMÉLIORÉ ==========
LOGS_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

# Fichiers de log du jour
def get_log_filename(log_type="api"):
    today = datetime.now().strftime("%Y-%m-%d")
    return os.path.join(LOGS_DIR, f"{log_type}-{today}.log")

# Format enrichi avec plus de contexte
LOG_FORMAT = '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# Logger principal
logger = logging.getLogger("kalga")
logger.setLevel(logging.DEBUG if settings.debug else logging.INFO)

# Handler fichier principal (INFO+)
file_handler = logging.FileHandler(get_log_filename("api"), encoding='utf-8')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))

# Handler fichier erreurs séparé (ERROR+)
error_handler = logging.FileHandler(get_log_filename("errors"), encoding='utf-8')
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))

# Handler console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG if settings.debug else logging.INFO)
console_handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))

# Ajout des handlers
logger.addHandler(file_handler)
logger.addHandler(error_handler)
logger.addHandler(console_handler)

# Nettoyage des vieux logs (garde 7 jours)
def cleanup_old_logs():
    """Supprime les fichiers de log de plus de 7 jours"""
    import glob
    from datetime import timedelta

    cutoff = datetime.now() - timedelta(days=7)
    for pattern in ["api-*.log", "errors-*.log"]:
        for log_file in glob.glob(os.path.join(LOGS_DIR, pattern)):
            try:
                # Extraire la date du nom de fichier
                basename = os.path.basename(log_file)
                date_str = basename.split("-", 1)[1].replace(".log", "")
                file_date = datetime.strptime(date_str, "%Y-%m-%d")
                if file_date < cutoff:
                    os.remove(log_file)
                    logger.info(f"Ancien log supprimé: {basename}")
            except (ValueError, OSError):
                pass

cleanup_old_logs()
# ==============================================

# Chemin vers le dossier uploads
UPLOADS_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads")

# Créer le dossier s'il n'existe pas
os.makedirs(UPLOADS_DIR, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialiser la base de données
    logger.info("=" * 50)
    logger.info("KALGA API - DÉMARRAGE")
    logger.info(f"Mode: {'DEBUG' if settings.debug else 'PRODUCTION'}")
    logger.info(f"Logs: {get_log_filename('api')}")
    logger.info(f"Erreurs: {get_log_filename('errors')}")
    logger.info("=" * 50)

    db = await get_db()

    # Créer l'admin par défaut si nécessaire
    try:
        user_repo = get_user_repository()
        await user_repo.ensure_admin_exists(
            settings.admin_email,
            settings.admin_password
        )
        logger.info(f"Admin par défaut vérifié: {settings.admin_email}")
    except Exception as e:
        logger.error(f"Erreur création admin: {e}")

    # Nettoyer les conversations expirées au démarrage
    try:
        await db.cleanup_expired_conversations(days=7)
        logger.info("Nettoyage des conversations expirées effectué")
    except Exception as e:
        logger.error(f"Erreur nettoyage conversations: {e}")

    # Démarrer le scheduler de relances automatiques
    followup_service = get_followup_service()
    await followup_service.start_scheduler(interval_seconds=60)
    logger.info("Scheduler de relances démarré")

    logger.info("KALGA API prête!")
    yield
    # Shutdown
    followup_service.stop_scheduler()
    logger.info("Arrêt KALGA API...")


app = FastAPI(
    title=settings.app_name,
    description="API WhatsApp Commerce Automation - Gestion des ventes via Status",
    version="1.0.0",
    lifespan=lifespan
)

# Rate Limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(merchants_router, prefix="/api")
app.include_router(products_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(merchant_commands_router, prefix="/api")
app.include_router(stats_router)
app.include_router(categories_router)
app.include_router(import_export_router)
app.include_router(away_mode_router)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(activation_router)
app.include_router(storefront_router)

# Servir les images statiques
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")

# Servir la vitrine publique
STOREFRONT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "storefront")
if os.path.exists(STOREFRONT_DIR):
    app.mount("/boutique", StaticFiles(directory=STOREFRONT_DIR, html=True), name="storefront")


@app.get("/")
async def root():
    return {
        "name": "KALGA API",
        "version": "1.0.0",
        "description": "WhatsApp Commerce Automation",
        "endpoints": {
            "merchants": "/api/merchants",
            "products": "/api/products",
            "chat": "/api/chat/incoming"
        }
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "kalga-api"}
