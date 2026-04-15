"""MCP server instance with all tools registered."""

import json
import logging
import functools
from fastmcp import FastMCP
from fastmcp.server.auth import TokenVerifier, AccessToken
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from src.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# JWT verifier: wraps our RS256 OAuth flow + legacy HS256 support
# ---------------------------------------------------------------------------


class MCPTokenVerifier(TokenVerifier):
    """
    FastMCP TokenVerifier that validates JWTs issued by our OAuth server.

    Supports RS256 tokens (issued via OAuth 2.1 flow for Claude/Cursor)
    and HS256 tokens (legacy mobile-app direct access).

    Uses FastMCP default resource URL behavior so WWW-Authenticate can point
    to path-scoped protected resource metadata for /sse requests.
    """

    async def verify_token(self, token: str) -> AccessToken | None:
        """Validate a Bearer token and return AccessToken if valid."""
        import jwt as pyjwt
        from src.oauth import get_rsa_public_pem

        try:
            # Peek at the algorithm without verifying to pick the right key
            try:
                header = pyjwt.get_unverified_header(token)
                alg = header.get("alg", "HS256")
            except pyjwt.DecodeError:
                logger.debug("verify_token: cannot decode header")
                return None

            base_url = settings.mcp_server_url.rstrip("/")
            valid_issuers = {
                settings.jwt_issuer,
                base_url,
            }

            if alg == "RS256":
                decode_key = get_rsa_public_pem()
                algorithms = ["RS256"]
            else:
                decode_key = settings.jwt_secret_key
                algorithms = [settings.jwt_algorithm]

            # Skip PyJWT audience validation: Claude may send the resource
            # URL in many forms (with/without trailing slash, with /sse path).
            # We do our own flexible audience check below.
            payload = pyjwt.decode(
                token,
                decode_key,
                algorithms=algorithms,
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_aud": False,  # manual check below
                    "require": ["sub", "exp"],
                },
            )

            # Flexible audience check: accept mcp:// legacy, exact base URL,
            # base URL with trailing slash, or any path under base URL.
            aud = payload.get("aud")
            if aud is not None:
                aud_list = [aud] if isinstance(aud, str) else aud

                def _aud_ok(a: str) -> bool:
                    return (
                        a == settings.mcp_audience
                        or a.rstrip("/") == base_url
                        or a.startswith(base_url + "/")
                    )

                if not any(_aud_ok(a) for a in aud_list):
                    logger.warning("verify_token: invalid audience %r (base=%r)", aud, base_url)
                    return None

            # Validate issuer if present
            iss = payload.get("iss")
            if iss and iss not in valid_issuers:
                logger.warning("verify_token: invalid issuer %r", iss)
                return None

            user_id = int(payload["sub"])
            scopes = payload.get("scope", "").split()
            exp = payload.get("exp")

            logger.info("verify_token: authenticated user_id=%d alg=%s", user_id, alg)
            return AccessToken(
                token=token,
                client_id=str(user_id),
                scopes=scopes,
                expires_at=int(exp) if exp else None,
            )

        except pyjwt.ExpiredSignatureError:
            logger.info("verify_token: token expired")
            return None
        except pyjwt.InvalidAudienceError:
            logger.warning("verify_token: invalid audience")
            return None
        except (pyjwt.PyJWTError, ValueError, TypeError) as exc:
            logger.warning(
                "verify_token: validation failed (%s): %s",
                type(exc).__name__,
                exc,
            )
            return None

    def _build_auth_info(self, request: Request):
        """
        Ensure WWW-Authenticate advertises /sse as protected resource metadata.
        This keeps RFC 9728 resource discovery consistent with Claude's configured
        MCP endpoint URL (https://.../sse).
        """
        info = super()._build_auth_info(request)
        try:
            base = self.base_url.rstrip("/")
            info.resource_metadata_url = f"{base}/.well-known/oauth-protected-resource/sse"
        except Exception:
            pass
        return info


# Create the JWT verifier — protects the SSE endpoint so Claude/Cursor see
# a proper 401 + WWW-Authenticate header and trigger the OAuth 2.1 flow.
_jwt_verifier = MCPTokenVerifier(
    base_url=settings.mcp_server_url.rstrip("/"),
    required_scopes=[],  # scope enforced per-tool via authenticate_from_context
)


# ---------------------------------------------------------------------------
# Logging middleware
# ---------------------------------------------------------------------------


class AuthDebugMiddleware(BaseHTTPMiddleware):
    """Log every request with its auth status to diagnose token issues."""

    async def dispatch(self, request: Request, call_next):
        auth = request.headers.get("Authorization", "")
        session_id = request.headers.get("Mcp-Session-Id", "")
        proto = request.headers.get(
            "MCP-Protocol-Version", request.headers.get("mcp-protocol-version", "")
        )
        accept = request.headers.get("Accept", "")

        # Log every request to /sse or OAuth endpoints for tracing
        is_sse = request.url.path in ("/sse", "/messages")
        is_oauth = request.url.path.startswith("/oauth") or request.url.path.startswith(
            "/.well-known"
        )
        if auth or is_sse or is_oauth:
            preview = (auth[:40] + "...") if len(auth) > 40 else auth
            logger.info(
                "[REQ] %s %s | Auth: %s | Session: %s | Proto: %s | Accept: %s",
                request.method,
                request.url.path,
                preview or "(none)",
                session_id or "(none)",
                proto or "(none)",
                accept[:60] or "(none)",
            )

        response = await call_next(request)

        if auth or is_sse or is_oauth or response.status_code in (400, 401, 403, 405):
            logger.info("[RES] %s %s → %d", request.method, request.url.path, response.status_code)

        return response


def _serialize(obj):
    """Serialize object to JSON-safe string, truncating if too long."""
    try:
        s = json.dumps(obj, ensure_ascii=False, default=str)
        if len(s) > 2000:
            s = s[:2000] + "... [truncated]"
        return s
    except Exception:
        return repr(obj)


def log_tool(fn):
    """Decorator that logs tool input parameters and output result."""

    @functools.wraps(fn)
    async def wrapper(*args, **kwargs):
        tool_name = fn.__name__
        import inspect

        sig = inspect.signature(fn)
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()
        params = {k: v for k, v in bound.arguments.items() if k != "ctx"}
        logger.info(f"[TOOL] {tool_name} INPUT: {_serialize(params)}")
        try:
            result = await fn(*args, **kwargs)
            logger.info(f"[TOOL] {tool_name} OUTPUT: {_serialize(result)}")
            return result
        except Exception as e:
            logger.error(f"[TOOL] {tool_name} ERROR: {e}")
            raise

    return wrapper


# ---------------------------------------------------------------------------
# MCP server instance — auth= ensures SSE endpoint returns 401 + WWW-Authenticate
# so Claude Code / Cursor trigger the OAuth 2.1 browser flow automatically.
# ---------------------------------------------------------------------------

mcp = FastMCP(
    name=settings.mcp_server_name,
    version=settings.mcp_server_version,
    instructions=(
        "MyTaskly è un'app mobile di gestione produttività. "
        "Questo server MCP permette di creare, consultare e modificare task, categorie e note dell'utente. "
        "I task hanno titolo, priorità (Alta/Media/Bassa), stato (In sospeso/Completato/Annullato), scadenza e categoria. "
        "Le categorie organizzano i task in gruppi (es. Lavoro, Casa, Sport). "
        "Le note sono post-it digitali con testo libero e colore. "
        "Usa i tool 'show_*' per visualizzare dati nell'app mobile, e i tool 'get_*' per elaborazione interna."
    ),
    auth=_jwt_verifier,
)

mcp.add_middleware(AuthDebugMiddleware)

# Import and register all tools
from src.tools.categories import (
    get_my_categories,
    create_category,
    update_category,
    show_categories_to_user,
    show_category_details,
)

from src.tools.tasks import (
    get_tasks,
    update_task,
    complete_task,
    get_task_stats,
    get_overdue_tasks,
    get_upcoming_tasks,
    add_task,
    show_tasks_to_user,
)

from src.tools.notes import get_notes, create_note, update_note, delete_note, show_notes_to_user

from src.tools.meta import add_multiple_tasks

from src.tools.health import health_check

# Register category tools
mcp.tool()(log_tool(get_my_categories))
mcp.tool()(log_tool(create_category))
mcp.tool()(log_tool(update_category))
mcp.tool()(log_tool(show_categories_to_user))
mcp.tool()(log_tool(show_category_details))

# Register task tools
mcp.tool()(log_tool(get_tasks))
mcp.tool()(log_tool(update_task))
mcp.tool()(log_tool(complete_task))
mcp.tool()(log_tool(get_task_stats))
mcp.tool()(log_tool(get_overdue_tasks))
mcp.tool()(log_tool(get_upcoming_tasks))
mcp.tool()(log_tool(add_task))
mcp.tool()(log_tool(show_tasks_to_user))

# Register note tools
mcp.tool()(log_tool(get_notes))
mcp.tool()(log_tool(create_note))
mcp.tool()(log_tool(update_note))
mcp.tool()(log_tool(delete_note))
mcp.tool()(log_tool(show_notes_to_user))

# Register meta tools
# mcp.tool()(log_tool(add_multiple_tasks))

# Register health check (no auth required)
# mcp.tool()(log_tool(health_check))

# ---------------------------------------------------------------------------
# OAuth 2.1 routes (Claude.ai / Claude Code support)
# ---------------------------------------------------------------------------
from src.oauth import (
    jwks_endpoint,
    protected_resource_metadata,
    authorization_server_metadata,
    dynamic_client_registration,
    authorize_get,
    authorize_post,
    token_endpoint,
)

# ---------------------------------------------------------------------------
# Health check — no auth required, used by Railway / load balancers
# ---------------------------------------------------------------------------
from starlette.responses import JSONResponse as _JSONResponse


async def _health_handler(request: Request) -> Response:
    return _JSONResponse({"status": "ok", "server": settings.mcp_server_name})  # type: ignore[return-value]


mcp.custom_route("/health", methods=["GET"])(_health_handler)

mcp.custom_route("/.well-known/jwks.json", methods=["GET"])(jwks_endpoint)
mcp.custom_route("/.well-known/oauth-protected-resource", methods=["GET"])(
    protected_resource_metadata
)
# Path-scoped variant: claude.ai first tries /.well-known/oauth-protected-resource/sse
# before falling back to the non-scoped form (RFC 9728 §4.2).
mcp.custom_route("/.well-known/oauth-protected-resource/sse", methods=["GET"])(
    protected_resource_metadata
)
mcp.custom_route("/.well-known/oauth-authorization-server", methods=["GET"])(
    authorization_server_metadata
)
mcp.custom_route("/oauth/register", methods=["POST"])(dynamic_client_registration)
mcp.custom_route("/oauth/authorize", methods=["GET"])(authorize_get)
mcp.custom_route("/oauth/authorize", methods=["POST"])(authorize_post)
mcp.custom_route("/oauth/token", methods=["POST"])(token_endpoint)
