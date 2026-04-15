#!/usr/bin/env python
"""
Run the MyTaskly MCP server with all registered tools.

Usage:
    python main.py              # Run MCP server in SSE mode (HTTP server)
"""

import os
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

try:
    from src.core.server import mcp
    from src.config import settings
    logger.info("Successfully imported server and settings")
except Exception as e:
    logger.error(f"Failed to import modules: {e}")
    sys.exit(1)


if __name__ == "__main__":
    try:
        # Get port from environment variable (Railway sets this)
        port = int(os.getenv("PORT", 8000))
        host = os.getenv("HOST", "0.0.0.0")

        logger.info(f"Configuration loaded:")
        logger.info(f"  - Host: {host}")
        logger.info(f"  - Port: {port}")
        logger.info(f"  - FastAPI URL: {settings.fastapi_base_url}")
        logger.info(f"  - MCP Server: {settings.mcp_server_name} v{settings.mcp_server_version}")

        # Run the MCP server in SSE mode for Railway deployment
        logger.info(f"Starting MCP server in SSE mode on {host}:{port}...")
        logger.info("Ready to accept HTTP connections")

        # Run with Streamable HTTP transport (handles both GET/SSE and POST/messages
        # at the same path).  claude.ai and Claude Code use POST to send messages,
        # which SSE-only mode rejects with 405.  "http" is an alias for
        # "streamable-http" in FastMCP 3.x.
        mcp.run(transport="http", path="/sse", host=host, port=port)
    except Exception as e:
        logger.error(f"Failed to start server: {e}", exc_info=True)
        sys.exit(1)
