"""Fixtures de test : base SQLite temporaire isolée."""
import os
import tempfile
from pathlib import Path

import pytest_asyncio

from app.database import connection
from app.database import db as db_module
from app.database.connection import init_database


@pytest_asyncio.fixture
async def temp_db(monkeypatch):
    """Crée une base SQLite temporaire isolée, schéma complet, nettoyée après le test."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    monkeypatch.setattr(connection, "DB_PATH", Path(path))
    # Réinitialise le singleton get_db() pour que chaque test reparte propre
    # (les repos lisent DB_PATH paresseusement, mais on évite toute fuite d'état).
    monkeypatch.setattr(db_module, "_db", None)
    await init_database()
    yield path
    try:
        os.remove(path)
    except OSError:
        pass
