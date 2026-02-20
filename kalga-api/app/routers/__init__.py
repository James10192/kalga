"""
Routers FastAPI pour KALGA
"""
from .merchants import router as merchants_router
from .products import router as products_router
from .chat import router as chat_router

# Utiliser le nouveau module refactorisé pour merchant_commands
from ..modules.merchant_commands import router as merchant_commands_router

__all__ = [
    "merchants_router",
    "products_router",
    "chat_router",
    "merchant_commands_router"
]
