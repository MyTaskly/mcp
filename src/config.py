"""Configuration management for MyTaskly MCP Server."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """MCP Server settings loaded from environment variables."""

    # FastAPI Server Configuration
    fastapi_base_url: str = "http://localhost:8080"
    fastapi_api_key: str = "test_api_key_123"

    # JWT Configuration (MUST match FastAPI server)
    jwt_secret_key: str = "change-this-secret-key-in-production"
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "https://api.mytasklyapp.com"
    mcp_audience: str = "mcp://mytaskly-mcp-server"

    # MCP Server Configuration
    mcp_server_name: str = "MyTaskly MCP Server"
    mcp_server_version: str = "0.1.1"
    # Public URL of this MCP server (used in OAuth discovery metadata).
    # In production set MCP_SERVER_URL=https://your-railway-domain.up.railway.app
    mcp_server_url: str = "http://localhost:8000"

    # Logging
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )


# Global settings instance
settings = Settings()
