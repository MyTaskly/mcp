"""MCP server instance with all tools registered."""

from fastmcp import FastMCP
from src.config import settings

# Create MCP server instance
mcp = FastMCP(
    name=settings.mcp_server_name,
    version=settings.mcp_server_version,
    instructions="MCP server for MyTaskly with OAuth 2.1 authentication and HTTP API integration"
)

# Import and register all tools
from src.tools.categories import (
    get_my_categories,
    create_category,
    update_category,
    search_categories,
    show_categories_to_user
)

from src.tools.tasks import (
    get_tasks,
    update_task,
    complete_task,
    get_task_stats,
    get_next_due_task,
    get_overdue_tasks,
    get_upcoming_tasks,
    add_task
)

from src.tools.notes import (
    get_notes,
    create_note,
    update_note,
    delete_note
)

from src.tools.meta import (
    get_or_create_category,
    move_all_tasks_between_categories,
    add_multiple_tasks
)

from src.tools.health import health_check

# Register category tools
mcp.tool()(get_my_categories)
mcp.tool()(create_category)
mcp.tool()(update_category)
mcp.tool()(search_categories)
mcp.tool()(show_categories_to_user)

# Register task tools
mcp.tool()(get_tasks)
mcp.tool()(update_task)
mcp.tool()(complete_task)
mcp.tool()(get_task_stats)
mcp.tool()(get_next_due_task)
mcp.tool()(get_overdue_tasks)
mcp.tool()(get_upcoming_tasks)
mcp.tool()(add_task)

# Register note tools
mcp.tool()(get_notes)
mcp.tool()(create_note)
mcp.tool()(update_note)
mcp.tool()(delete_note)

# Register meta tools
mcp.tool()(get_or_create_category)
mcp.tool()(move_all_tasks_between_categories)
mcp.tool()(add_multiple_tasks)

# Register health check (no auth required)
mcp.tool()(health_check)
