"""Fixtures de test : base SQLite temporaire isolée."""
import os
import tempfile
from pathlib import Path

import pytest_asyncio

from app.database import connection
from app.database.connection import init_database


@pytest_asyncio.fixture
async def temp_db(monkeypatch):
    """Crée une base SQLite temporaire isolée, schéma complet, nettoyée après le test."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    monkeypatch.setattr(connection, "DB_PATH", Path(path))
    await init_database()
    yield path
    try:
        os.remove(path)
    except OSError:
        pass
