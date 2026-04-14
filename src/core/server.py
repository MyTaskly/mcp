"""MCP server instance with all tools registered."""

import json
import logging
import functools
from fastmcp import FastMCP
from src.config import settings

logger = logging.getLogger(__name__)


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
        # Build a dict of all non-ctx args for logging
        import inspect
        sig = inspect.signature(fn)
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()
        params = {
            k: v for k, v in bound.arguments.items()
            if k != "ctx"
        }
        logger.info(f"[TOOL] {tool_name} INPUT: {_serialize(params)}")
        try:
            result = await fn(*args, **kwargs)
            logger.info(f"[TOOL] {tool_name} OUTPUT: {_serialize(result)}")
            return result
        except Exception as e:
            logger.error(f"[TOOL] {tool_name} ERROR: {e}")
            raise
    return wrapper


# Create MCP server instance
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
    )
)

# Import and register all tools
from src.tools.categories import (
    get_my_categories,
    create_category,
    update_category,
    show_categories_to_user,
    show_category_details
)

from src.tools.tasks import (
    get_tasks,
    update_task,
    complete_task,
    get_task_stats,
    get_overdue_tasks,
    get_upcoming_tasks,
    add_task,
    show_tasks_to_user
)

from src.tools.notes import (
    get_notes,
    create_note,
    update_note,
    delete_note,
    show_notes_to_user
)

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
    protected_resource_metadata,
    authorization_server_metadata,
    dynamic_client_registration,
    authorize_get,
    authorize_post,
    token_endpoint,
)

mcp.custom_route("/.well-known/oauth-protected-resource",  methods=["GET"])(protected_resource_metadata)
mcp.custom_route("/.well-known/oauth-authorization-server", methods=["GET"])(authorization_server_metadata)
mcp.custom_route("/oauth/register",  methods=["POST"])(dynamic_client_registration)
mcp.custom_route("/oauth/authorize", methods=["GET"])(authorize_get)
mcp.custom_route("/oauth/authorize", methods=["POST"])(authorize_post)
mcp.custom_route("/oauth/token",     methods=["POST"])(token_endpoint)
