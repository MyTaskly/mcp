"""HTTP client for making authenticated requests to FastAPI server."""

import httpx
from typing import Dict, Any, List, Optional
from src.config import settings


class FastAPIClient:
    """Client for communicating with MyTaskly FastAPI server."""

    def __init__(self):
        self.base_url = settings.fastapi_base_url
        self.api_key = settings.fastapi_api_key
        self.headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }

    async def _get_user_token(self, user_id: int) -> str:
        """
        Generate a JWT token for the user to authenticate with FastAPI.

        This token is separate from the MCP authentication token.
        It's used by the MCP server to act on behalf of the user when
        calling FastAPI backend endpoints.

        Token format matches FastAPI server expectations:
        - sub: user_id as string (FastAPI accepts numeric user IDs)
        - type: "access" (required by FastAPI)
        - exp: expiration timestamp (30 minutes)
        """
        import jwt
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(user_id),  # FastAPI accepts user_id as username
            "type": "access",      # Required by FastAPI token validation
            "exp": int((now + timedelta(minutes=30)).timestamp()),
        }

        # Use the same SECRET_KEY as FastAPI for user authentication
        # This MUST match the SECRET_KEY in MyTaskly-server config.py
        secret_key = "349878uoti34h80943iotrhf-83490ewofridsh3t4iner"
        token = jwt.encode(payload, secret_key, algorithm="HS256")
        return token

    async def get_tasks(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Get all tasks for a user.

        Args:
            user_id: User ID to fetch tasks for

        Returns:
            List of task dictionaries
        """
        token = await self._get_user_token(user_id)
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key,
            "Authorization": f"Bearer {token}"
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/tasks/",
                headers=headers
            )
            response.raise_for_status()
            return response.json()

    async def get_categories(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Get all categories for a user.

        Args:
            user_id: User ID to fetch categories for

        Returns:
            List of category dictionaries
        """
        token = await self._get_user_token(user_id)
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key,
            "Authorization": f"Bearer {token}"
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/categories/",
                headers=headers
            )
            response.raise_for_status()
            return response.json()

    async def create_task(
        self,
        user_id: int,
        title: str,
        category_id: int,
        description: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        priority: str = "Media",
        status: str = "In sospeso"
    ) -> Dict[str, Any]:
        """
        Create a new task for a user.

        Args:
            user_id: User ID to create task for
            title: Task title
            category_id: Category ID for the task
            description: Optional task description
            start_time: Optional start time (format: YYYY-MM-DD HH:MM:SS)
            end_time: Optional end time (format: YYYY-MM-DD HH:MM:SS)
            priority: Task priority (Alta, Media, Bassa)
            status: Task status (In sospeso, Completato, Annullato)

        Returns:
            Created task dictionary
        """
        token = await self._get_user_token(user_id)
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key,
            "Authorization": f"Bearer {token}"
        }

        task_data = {
            "title": title,
            "category_id": category_id,
            "priority": priority,
            "status": status
        }

        if description:
            task_data["description"] = description
        if start_time:
            task_data["start_time"] = start_time
        if end_time:
            task_data["end_time"] = end_time

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/tasks",  # No trailing slash!
                headers=headers,
                json=task_data
            )
            response.raise_for_status()
            return response.json()

    async def create_note(
        self,
        user_id: int,
        title: str,
        position_x: str = "0",
        position_y: str = "0",
        color: str = "#FFEB3B"
    ) -> Dict[str, Any]:
        """
        Create a new note for a user.

        Args:
            user_id: User ID to create note for
            title: Note text content
            position_x: X position on canvas
            position_y: Y position on canvas
            color: Note color in hex format

        Returns:
            Created note dictionary
        """
        token = await self._get_user_token(user_id)
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key,
            "Authorization": f"Bearer {token}"
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/notes",
                headers=headers,
                json={
                    "user_id": user_id,
                    "title": title,
                    "position_x": position_x,
                    "position_y": position_y,
                    "color": color
                }
            )
            response.raise_for_status()
            result = response.json()

            # FastAPI returns {"note_id": ..., "status_code": 201}
            # Transform to expected format with all fields
            return {
                "note_id": result["note_id"],
                "title": title,
                "color": color,
                "position_x": position_x,
                "position_y": position_y,
                "message": "[OK] Nota creata con successo"
            }

    async def health_check(self) -> Dict[str, Any]:
        """
        Check if FastAPI server is healthy.

        Returns:
            Health status dictionary
        """
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(f"{self.base_url}/health")
                return {"status": "healthy", "code": response.status_code}
            except Exception as e:
                return {"status": "unhealthy", "error": str(e)}


# Global client instances
fastapi_client = FastAPIClient()
task_client = fastapi_client  # Alias for task operations
category_client = fastapi_client  # Alias for category operations
note_client = fastapi_client  # Alias for note operations
