"""MCP health check tool."""

from typing import Dict, Any
from src.client import health_client
from src.config import settings


async def health_check() -> Dict[str, Any]:
    """Verifica lo stato di salute del server MCP e del backend FastAPI. Non richiede autenticazione.

    Quando usare:
    - "Il server funziona?", "Sei online?", diagnostica errori di connessione
    """
    fastapi_health = await health_client.health_check()

    return {
        "mcp_server": "healthy",
        "fastapi_server": fastapi_health.get("status", "unknown"),
        "fastapi_url": settings.fastapi_base_url,
        "fastapi_details": fastapi_health
    }
