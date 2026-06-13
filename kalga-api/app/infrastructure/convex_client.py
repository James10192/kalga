"""
Client Convex pour le backend Python (server-to-server).

Convex est la source de vérité unique (décision D3). Le backend FastAPI appelle
les fonctions internes Convex sans session utilisateur navigateur : il prouve sa
légitimité avec un secret partagé (`internalKey` = `INTERNAL_API_KEY`), validé
côté Convex par `assertInternalKey`.

Usage :

    from app.infrastructure.convex_client import get_convex

    convex = get_convex()
    ctx = await convex.query("internal/chat:getContext", {
        "merchantPhone": "2250700000000",
        "clientPhone": "2250500000001",
        "productCode": "SNK01",
    })

Le nom de fonction suit la convention `"module:export"`. Pour un module dans un
sous-dossier (`convex/internal/chat.ts`), le chemin est `"internal/chat:export"`.

Pièges (cf. plans/reference/convex-python-client.md) :
- Le client `ConvexClient` est SYNCHRONE et basé WebSocket : on l'instancie une
  seule fois (singleton) et on wrappe les appels en `asyncio.to_thread` pour ne
  pas bloquer l'event loop FastAPI.
- Un `int` Python est envoyé comme Float64 : OK pour nos quantités/prix.
- `internalKey` est injecté automatiquement dans chaque appel (jamais à la main).
"""
import asyncio
import logging
from typing import Any, Dict, Optional

# NB import paresseux de `settings` (dans get_convex) : importer
# `app.core.config` au chargement du module crée un cycle quand un repo importe
# ce client au top-level (app.database -> repo -> convex_client -> app.core ->
# events -> app.database, encore en cours d'init). Voir Phase E2.

logger = logging.getLogger("kalga.convex")


class ConvexBackendClient:
    """Wrapper fin autour de `convex.ConvexClient` qui injecte `internalKey`."""

    def __init__(self, url: str, admin_key: Optional[str] = None, internal_key: str = ""):
        if not url:
            raise RuntimeError(
                "CONVEX_URL non configurée — impossible d'initialiser le client Convex."
            )
        # Import paresseux : le package `convex` n'est requis que si on utilise Convex.
        from convex import ConvexClient

        self._client = ConvexClient(url)
        self._internal_key = internal_key
        if admin_key:
            # Accès privilégié server-to-server (internalQuery/internalMutation).
            self._client.set_admin_auth(admin_key)

    def _with_key(self, args: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Injecte `internalKey` dans les arguments (objet dict unique)."""
        merged = dict(args or {})
        merged["internalKey"] = self._internal_key
        return merged

    async def query(self, name: str, args: Optional[Dict[str, Any]] = None) -> Any:
        """Appelle une query interne Convex (lecture seule, retry réseau auto)."""
        return await asyncio.to_thread(self._client.query, name, self._with_key(args))

    async def mutation(self, name: str, args: Optional[Dict[str, Any]] = None) -> Any:
        """Appelle une mutation interne Convex (écriture transactionnelle)."""
        return await asyncio.to_thread(self._client.mutation, name, self._with_key(args))

    async def action(self, name: str, args: Optional[Dict[str, Any]] = None) -> Any:
        """Appelle une action interne Convex (effets de bord / appels tiers)."""
        return await asyncio.to_thread(self._client.action, name, self._with_key(args))


# === Singleton ===
_convex: Optional[ConvexBackendClient] = None


def get_convex() -> ConvexBackendClient:
    """
    Retourne l'instance singleton du client Convex (connexion WebSocket persistante).
    Lève si `CONVEX_URL` n'est pas configurée.
    """
    global _convex
    if _convex is None:
        from app.core.config import settings
        _convex = ConvexBackendClient(
            url=settings.convex_url,
            admin_key=settings.convex_admin_key,
            internal_key=settings.internal_api_key,
        )
        logger.info("Client Convex initialisé (%s)", settings.convex_url)
    return _convex
