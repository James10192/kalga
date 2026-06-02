"""Transparent proxy from /api/wa/* to the local WhatsApp bridge.

Lets the browser talk to the bridge without exposing port 3001 publicly:
the bridge binds to 127.0.0.1, the FastAPI (reachable via tunnel) relays calls.
"""
from fastapi import APIRouter, Request
from fastapi.responses import Response
import httpx

from ..config import settings

router = APIRouter(prefix="/api/wa", tags=["WhatsApp Bridge Proxy"])

_STRIPPED_REQUEST_HEADERS = {"host", "content-length", "connection"}
_STRIPPED_RESPONSE_HEADERS = {"content-length", "transfer-encoding", "connection"}


@router.api_route("/{path:path}", methods=["GET", "POST", "DELETE", "PUT", "PATCH"])
async def proxy(path: str, request: Request):
    url = f"{settings.whatsapp_bridge_url.rstrip('/')}/{path}"
    headers = {k: v for k, v in request.headers.items() if k.lower() not in _STRIPPED_REQUEST_HEADERS}
    body = await request.body()

    async with httpx.AsyncClient(timeout=settings.whatsapp_request_timeout) as client:
        upstream = await client.request(
            request.method,
            url,
            content=body,
            params=request.query_params,
            headers=headers,
        )

    response_headers = {
        k: v for k, v in upstream.headers.items()
        if k.lower() not in _STRIPPED_RESPONSE_HEADERS
    }
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=response_headers,
        media_type=upstream.headers.get("content-type"),
    )
