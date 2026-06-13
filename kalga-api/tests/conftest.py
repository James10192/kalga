"""Fixtures de test.

Phase F : SQLite entièrement supprimé. L'ancienne fixture `temp_db` créait une
base SQLite temporaire ; le data layer est désormais 100 % Convex. Les tests qui
dépendaient du seeding SQLite sont marqués `pytest.mark.skip` (à réécrire avec un
seeding Convex, cf. tests/test_chat_convex.py).

`temp_db` est conservée comme stub inerte uniquement pour que ces modules
skippés restent collectables (ils référencent encore le nom de la fixture). Elle
ne crée aucune base et n'est jamais exécutée (tests skippés en amont).
"""
import pytest_asyncio


@pytest_asyncio.fixture
async def temp_db():
    """Stub inerte — SQLite supprimé (Phase F). Réservé aux tests skippés."""
    yield None
