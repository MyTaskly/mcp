"""OAuth 2.1 JWT authentication middleware for MCP Server."""

import jwt
import logging
from typing import Optional
from datetime import datetime, timezone
from fastapi import HTTPException, Header
from fastmcp import Context
from fastmcp.server.dependencies import get_http_request
from src.config import settings


def _www_authenticate_header() -> str:
    """Build WWW-Authenticate header with OAuth discovery URL for RFC 9728."""
    base = settings.mcp_server_url.rstrip("/")
    return (
        f'Bearer realm="mcp", '
        f'resource_metadata="{base}/.well-known/oauth-protected-resource"'
    )

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Custom exception for authentication errors."""
    pass


def extract_token_from_context(ctx: Context) -> str:
    """
    Extract JWT token from MCP Context (SSE request headers).

    This function retrieves the Authorization header from the HTTP request
    that established the SSE connection. This is the secure way to handle
    authentication in MCP tools - the token stays in the HTTP header and
    is never exposed to the LLM.

    Args:
        ctx: FastMCP Context object containing request information

    Returns:
        authorization: Authorization header string "Bearer <token>"

    Raises:
        HTTPException: If Authorization header is missing or invalid
    """
    try:
        # Use the correct method to get HTTP request
        request = get_http_request()
        authorization = request.headers.get("Authorization") or request.headers.get("authorization")

        if not authorization:
            raise HTTPException(
                status_code=401,
                detail="Missing Authorization header in SSE connection",
                headers={"WWW-Authenticate": _www_authenticate_header()}
            )

        return authorization

    except (AttributeError, RuntimeError) as e:
        # Context doesn't have HTTP request (e.g., stdio mode) or not in HTTP context
        raise HTTPException(
            status_code=401,
            detail=f"Cannot extract Authorization header from context: {str(e)}",
            headers={"WWW-Authenticate": _www_authenticate_header()}
        )


def verify_jwt_token(authorization: Optional[str] = Header(None)) -> int:
    """
    Verify JWT token and extract user_id.

    This implements OAuth 2.1 Resource Server token validation.
    The MCP server acts as a Resource Server, validating tokens
    issued by the FastAPI Authorization Server.

    Args:
        authorization: Authorization header with format "Bearer <token>"

    Returns:
        user_id: Integer user ID extracted from token

    Raises:
        HTTPException: If token is missing, invalid, or expired
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": _www_authenticate_header()}
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Invalid Authorization header format. Expected: Bearer <token>",
            headers={"WWW-Authenticate": _www_authenticate_header()}
        )

    token = authorization.replace("Bearer ", "").strip()

    try:
        # Decode and validate JWT.
        # Accept both audiences:
        #   - mcp_audience: legacy value used by the mobile app
        #   - mcp_server_url: public URL used by OAuth-issued tokens (Claude / Claude Code)
        valid_audiences = [
            settings.mcp_audience,
            settings.mcp_server_url.rstrip("/"),
        ]
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            audience=valid_audiences,
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_aud": True,
                "require": ["sub", "aud", "exp", "iat"]
            }
        )

        # Extract user_id from "sub" claim
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise AuthenticationError("Token missing 'sub' claim")

        try:
            user_id = int(user_id_str)
        except (ValueError, TypeError):
            raise AuthenticationError(f"Invalid 'sub' claim format: {user_id_str}")

        # Validate issuer: accept both the legacy FastAPI issuer and the MCP
        # server's own URL (used by OAuth-issued tokens).
        if "iss" in payload:
            valid_issuers = {
                settings.jwt_issuer,
                settings.mcp_server_url.rstrip("/"),
            }
            if payload["iss"] not in valid_issuers:
                raise AuthenticationError(f"Invalid issuer: {payload['iss']}")

        # Optional: Log successful authentication
        logger.info(f"Authenticated user_id={user_id}")

        return user_id

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Token has expired",
            headers={"WWW-Authenticate": _www_authenticate_header() + ', error="invalid_token", error_description="Token expired"'}
        )

    except jwt.InvalidAudienceError:
        raise HTTPException(
            status_code=401,
            detail=f"Invalid token audience. Expected: {settings.mcp_audience}",
            headers={"WWW-Authenticate": _www_authenticate_header() + ', error="invalid_token", error_description="Invalid audience"'}
        )

    except jwt.InvalidSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Invalid token signature",
            headers={"WWW-Authenticate": _www_authenticate_header() + ', error="invalid_token", error_description="Invalid signature"'}
        )

    except jwt.DecodeError as e:
        raise HTTPException(
            status_code=401,
            detail=f"Token decode error: {str(e)}",
            headers={"WWW-Authenticate": _www_authenticate_header() + ', error="invalid_token", error_description="Malformed token"'}
        )

    except AuthenticationError as e:
        raise HTTPException(
            status_code=401,
            detail=str(e),
            headers={"WWW-Authenticate": _www_authenticate_header() + ', error="invalid_token"'}
        )

    except Exception as e:
        logger.error(f"Unexpected authentication error: {e}")
        raise HTTPException(
            status_code=401,
            detail="Authentication failed",
            headers={"WWW-Authenticate": _www_authenticate_header() + ', error="invalid_token"'}
        )


def authenticate_from_context(ctx: Context) -> int:
    """
    Authenticate user from MCP Context and return user_id.

    This is the recommended function for MCP tools using SSE transport.
    It extracts the Authorization header from the SSE connection and
    validates the JWT token.

    Args:
        ctx: FastMCP Context object

    Returns:
        user_id: Integer user ID extracted from validated token

    Raises:
        HTTPException: If authentication fails for any reason

    Example usage in MCP tool:
        ```python
        from fastmcp import Context
        from src.auth import authenticate_from_context

        async def my_tool(ctx: Context, param1: str) -> Dict[str, Any]:
            user_id = authenticate_from_context(ctx)
            # ... rest of tool logic
        ```
    """
    authorization = extract_token_from_context(ctx)
    return verify_jwt_token(authorization)


def create_test_token(user_id: int, expires_minutes: int = 30) -> str:
    """
    Create a test JWT token for development/testing.

    In production, tokens should ONLY be created by the FastAPI Authorization Server.
    This function is for testing the MCP server independently.

    Args:
        user_id: User ID to encode in token
        expires_minutes: Token expiration time in minutes

    Returns:
        JWT token string
    """
    from datetime import timedelta

    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "aud": settings.mcp_audience,
        "iss": "https://api.mytasklyapp.com",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=expires_minutes)).timestamp()),
        "scope": "tasks:read tasks:write categories:read categories:write notes:read notes:write"
    }

    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token
