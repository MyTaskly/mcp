"""
OAuth 2.1 Authorization Server implementation for MyTaskly MCP Server.

Implements:
  - RFC 9728: Protected Resource Metadata  (/.well-known/oauth-protected-resource)
  - RFC 8414: Authorization Server Metadata (/.well-known/oauth-authorization-server)
  - RFC 7591: Dynamic Client Registration   (POST /oauth/register)
  - OAuth 2.1 + PKCE Authorization Code flow (GET/POST /oauth/authorize)
  - Token endpoint with PKCE verification   (POST /oauth/token)

All route handlers are plain async functions (Request -> Response) meant to be
registered on the FastMCP instance with @mcp.custom_route(...).
"""

import hashlib
import base64
import secrets
import uuid
import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

import httpx
import jwt
from starlette.requests import Request
from starlette.responses import JSONResponse, HTMLResponse, RedirectResponse, Response

from src.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory stores (single-process; fine for Railway / single-dyno deploys)
# ---------------------------------------------------------------------------

# client_id -> { client_name, redirect_uris, grant_types, ... }
_clients: dict[str, dict] = {}

# code -> { user_id, client_id, redirect_uri, code_challenge,
#           code_challenge_method, expires_at }
_auth_codes: dict[str, dict] = {}


def _purge_expired_codes() -> None:
    """Remove expired authorization codes to prevent unbounded growth."""
    now = datetime.now(timezone.utc)
    expired = [k for k, v in _auth_codes.items() if v["expires_at"] < now]
    for k in expired:
        del _auth_codes[k]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_login_html() -> str:
    template_path = os.path.join(os.path.dirname(__file__), "templates", "login.html")
    with open(template_path, "r", encoding="utf-8") as f:
        return f.read()


def _verify_pkce(code_verifier: str, code_challenge: str, method: str = "S256") -> bool:
    """Verify PKCE S256 code_verifier against the stored code_challenge."""
    if method != "S256":
        return False
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    computed = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return secrets.compare_digest(computed, code_challenge)


def _issue_mcp_jwt(user_id: int, expires_minutes: int = 60) -> str:
    """
    Issue a JWT for the OAuth flow.
    Audience is set to the public MCP server URL so that Claude (which passes
    resource=<mcp_server_url> in the authorize request) accepts the token.
    verify_jwt_token() is updated to accept this audience as well.
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "aud": settings.mcp_server_url.rstrip("/"),
        "iss": settings.jwt_issuer,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=expires_minutes)).timestamp()),
        "scope": "mcp:tools",
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


async def _authenticate_user(username: str, password: str) -> Optional[int]:
    """
    Authenticate against the FastAPI backend.
    Step 1: POST /auth/login  → bearer_token (sub = username string)
    Step 2: GET  /auth/me     → {"id": "<user_id>", ...}  (integer user_id)
    Returns user_id on success, None on failure.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            # Step 1 — login
            resp = await client.post(
                f"{settings.fastapi_base_url}/auth/login",
                headers={
                    "X-API-Key": settings.fastapi_api_key,
                    "Content-Type": "application/json",
                },
                json={"username": username, "password": password},
            )
            if resp.status_code != 200:
                logger.warning("FastAPI login returned %d for user %r", resp.status_code, username)
                return None

            bearer_token = resp.json().get("bearer_token")
            if not bearer_token:
                logger.error("FastAPI login response missing bearer_token")
                return None

            # Step 2 — resolve integer user_id via /auth/me
            me_resp = await client.get(
                f"{settings.fastapi_base_url}/auth/me",
                headers={
                    "X-API-Key": settings.fastapi_api_key,
                    "Authorization": f"Bearer {bearer_token}",
                },
            )
            if me_resp.status_code != 200:
                logger.error("GET /auth/me returned %d", me_resp.status_code)
                return None

            user_id_str = me_resp.json().get("id")
            return int(user_id_str) if user_id_str else None

        except (httpx.HTTPError, ValueError, TypeError) as exc:
            logger.error("Authentication error: %s", exc)
            return None


def _render_login(
    client_name: str,
    client_id: str,
    redirect_uri: str,
    code_challenge: str,
    code_challenge_method: str,
    state: str,
    error: str = "",
) -> str:
    html = _load_login_html()
    replacements = {
        "{{client_name}}": client_name,
        "{{client_id}}": client_id,
        "{{redirect_uri}}": redirect_uri,
        "{{code_challenge}}": code_challenge,
        "{{code_challenge_method}}": code_challenge_method,
        "{{state}}": state,
        "{{error}}": error,
        "{{error_display}}": "flex" if error else "none",
    }
    for placeholder, value in replacements.items():
        html = html.replace(placeholder, value)
    return html


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------

async def protected_resource_metadata(request: Request) -> Response:
    """GET /.well-known/oauth-protected-resource  (RFC 9728)"""
    base = settings.mcp_server_url.rstrip("/")
    return JSONResponse(
        {
            "resource": base,
            "authorization_servers": [base],
            "scopes_supported": ["mcp:tools"],
            "bearer_methods_supported": ["header"],
        },
        headers={"Cache-Control": "no-store"},
    )


async def authorization_server_metadata(request: Request) -> Response:
    """GET /.well-known/oauth-authorization-server  (RFC 8414)"""
    base = settings.mcp_server_url.rstrip("/")
    return JSONResponse(
        {
            "issuer": base,
            "authorization_endpoint": f"{base}/oauth/authorize",
            "token_endpoint": f"{base}/oauth/token",
            "registration_endpoint": f"{base}/oauth/register",
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code"],
            "code_challenge_methods_supported": ["S256"],
            "token_endpoint_auth_methods_supported": ["none"],
            "scopes_supported": ["mcp:tools"],
        },
        headers={"Cache-Control": "no-store"},
    )


async def dynamic_client_registration(request: Request) -> Response:
    """POST /oauth/register  (RFC 7591 — Dynamic Client Registration)"""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            {"error": "invalid_request", "error_description": "Body must be JSON"},
            status_code=400,
        )

    redirect_uris = body.get("redirect_uris", [])
    if not redirect_uris or not isinstance(redirect_uris, list):
        return JSONResponse(
            {"error": "invalid_request", "error_description": "redirect_uris required"},
            status_code=400,
        )

    client_id = str(uuid.uuid4())
    record = {
        "client_id": client_id,
        "client_name": body.get("client_name", "MCP Client"),
        "redirect_uris": redirect_uris,
        "grant_types": body.get("grant_types", ["authorization_code"]),
        "response_types": body.get("response_types", ["code"]),
        "token_endpoint_auth_method": body.get("token_endpoint_auth_method", "none"),
    }
    _clients[client_id] = record
    logger.info("Registered new OAuth client: %s (%s)", client_id, record["client_name"])
    return JSONResponse(record, status_code=201)


async def authorize_get(request: Request) -> Response:
    """GET /oauth/authorize — show login form"""
    p = dict(request.query_params)

    if p.get("response_type") != "code":
        return JSONResponse({"error": "unsupported_response_type"}, status_code=400)

    client_id = p.get("client_id", "")
    if client_id not in _clients:
        return JSONResponse(
            {"error": "invalid_client", "error_description": "Unknown client_id"},
            status_code=400,
        )

    client = _clients[client_id]
    redirect_uri = p.get("redirect_uri", "")
    if redirect_uri not in client["redirect_uris"]:
        return JSONResponse(
            {"error": "invalid_request", "error_description": "redirect_uri not allowed"},
            status_code=400,
        )

    code_challenge = p.get("code_challenge", "")
    if not code_challenge:
        return JSONResponse(
            {"error": "invalid_request", "error_description": "code_challenge required (PKCE)"},
            status_code=400,
        )

    html = _render_login(
        client_name=client["client_name"],
        client_id=client_id,
        redirect_uri=redirect_uri,
        code_challenge=code_challenge,
        code_challenge_method=p.get("code_challenge_method", "S256"),
        state=p.get("state", ""),
    )
    return HTMLResponse(html)


async def authorize_post(request: Request) -> Response:
    """POST /oauth/authorize — process login form"""
    try:
        form = await request.form()
    except Exception:
        return JSONResponse({"error": "invalid_request"}, status_code=400)

    client_id = str(form.get("client_id", ""))
    redirect_uri = str(form.get("redirect_uri", ""))
    code_challenge = str(form.get("code_challenge", ""))
    code_challenge_method = str(form.get("code_challenge_method", "S256"))
    state = str(form.get("state", ""))
    username = str(form.get("username", "")).strip()
    password = str(form.get("password", ""))

    if client_id not in _clients:
        return JSONResponse({"error": "invalid_client"}, status_code=400)
    client = _clients[client_id]

    if redirect_uri not in client["redirect_uris"]:
        return JSONResponse({"error": "invalid_request"}, status_code=400)

    # --- Authenticate ---
    user_id = await _authenticate_user(username, password)
    if user_id is None:
        html = _render_login(
            client_name=client["client_name"],
            client_id=client_id,
            redirect_uri=redirect_uri,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            state=state,
            error="Credenziali non valide. Controlla username e password.",
        )
        return HTMLResponse(html, status_code=401)

    # --- Issue authorization code ---
    _purge_expired_codes()
    code = secrets.token_urlsafe(32)
    _auth_codes[code] = {
        "user_id": user_id,
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "code_challenge": code_challenge,
        "code_challenge_method": code_challenge_method,
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=10),
    }

    sep = "&" if "?" in redirect_uri else "?"
    location = f"{redirect_uri}{sep}code={code}"
    if state:
        location += f"&state={state}"

    logger.info("Auth code issued for user_id=%d, client=%s", user_id, client_id)
    return RedirectResponse(location, status_code=302)


async def token_endpoint(request: Request) -> Response:
    """POST /oauth/token — exchange code for access token"""
    try:
        form = await request.form()
    except Exception:
        return JSONResponse({"error": "invalid_request"}, status_code=400)

    grant_type = str(form.get("grant_type", ""))
    code = str(form.get("code", ""))
    redirect_uri = str(form.get("redirect_uri", ""))
    client_id = str(form.get("client_id", ""))
    code_verifier = str(form.get("code_verifier", ""))

    if grant_type != "authorization_code":
        return JSONResponse({"error": "unsupported_grant_type"}, status_code=400)

    if not all([code, redirect_uri, client_id, code_verifier]):
        return JSONResponse(
            {"error": "invalid_request", "error_description": "Missing required parameters"},
            status_code=400,
        )

    code_data = _auth_codes.get(code)
    if not code_data:
        return JSONResponse(
            {"error": "invalid_grant", "error_description": "Unknown or already-used code"},
            status_code=400,
        )

    if datetime.now(timezone.utc) > code_data["expires_at"]:
        del _auth_codes[code]
        return JSONResponse(
            {"error": "invalid_grant", "error_description": "Authorization code expired"},
            status_code=400,
        )

    if code_data["client_id"] != client_id:
        return JSONResponse(
            {"error": "invalid_grant", "error_description": "client_id mismatch"},
            status_code=400,
        )

    if code_data["redirect_uri"] != redirect_uri:
        return JSONResponse(
            {"error": "invalid_grant", "error_description": "redirect_uri mismatch"},
            status_code=400,
        )

    if not _verify_pkce(code_verifier, code_data["code_challenge"], code_data["code_challenge_method"]):
        return JSONResponse(
            {"error": "invalid_grant", "error_description": "PKCE verification failed"},
            status_code=400,
        )

    # One-time use — delete immediately
    del _auth_codes[code]

    user_id = code_data["user_id"]
    access_token = _issue_mcp_jwt(user_id, expires_minutes=60)

    logger.info("Access token issued for user_id=%d via OAuth flow", user_id)
    return JSONResponse(
        {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": "mcp:tools",
        },
        headers={"Cache-Control": "no-store", "Pragma": "no-cache"},
    )
