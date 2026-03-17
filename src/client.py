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
        token = jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")
        return token

    async def get_tasks(
        self,
        user_id: int,
        category_id: Optional[int] = None,
        priority: Optional[str] = None,
        status: Optional[str] = None,
        task_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get tasks for a user with optional client-side filtering.

        Uses /tasks/by-category-id/{id} when category_id is provided,
        otherwise fetches all tasks from /tasks/ and filters in Python.
        """
        token = await self._get_user_token(user_id)
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key,
            "Authorization": f"Bearer {token}"
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            if category_id is not None:
                response = await client.get(
                    f"{self.base_url}/tasks/by-category-id/{category_id}",
                    headers=headers
                )
            else:
                response = await client.get(
                    f"{self.base_url}/tasks/",
                    headers=headers
                )
            response.raise_for_status()
            tasks = response.json()

        # Client-side filtering for fields not exposed as server query params
        if task_id is not None:
            tasks = [t for t in tasks if t.get("task_id") == task_id]
        if priority is not None:
            tasks = [t for t in tasks if t.get("priority") == priority]
        if status is not None:
            tasks = [t for t in tasks if t.get("status") == status]

        return tasks

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
        end_time: Optional[str] = None,
        duration_minutes: Optional[int] = None,
        priority: str = "Media",
        status: str = "In sospeso"
    ) -> Dict[str, Any]:
        """
        Create a new task for a user.

        Note: start_time is always set server-side to now(), do not pass it.
        end_time must be a naive datetime string in the user's local timezone
        (format: "YYYY-MM-DD HH:MM:SS"); the server converts it to UTC.
        """
        token = await self._get_user_token(user_id)
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key,
            "Authorization": f"Bearer {token}"
        }

        # "user" field is required by TaskIn schema but immediately discarded by the server CRUD
        task_data: Dict[str, Any] = {
            "title": title,
            "category_id": category_id,
            "priority": priority,
            "status": status,
            "user": "",
        }

        if description:
            task_data["description"] = description
        if end_time:
            task_data["end_time"] = end_time
        if duration_minutes is not None:
            task_data["duration_minutes"] = duration_minutes

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/tasks",
                headers=headers,
                json=task_data
            )
            response.raise_for_status()
            return response.json()

    async def update_task(
        self,
        user_id: int,
        task_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        duration_minutes: Optional[int] = None,
        priority: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Update an existing task via PUT /tasks/{task_id}.

        Only pass the fields you want to change.
        end_time and start_time must be naive datetime strings in the user's
        local timezone (format: "YYYY-MM-DD HH:MM:SS"); the server converts to UTC.
        """
        token = await self._get_user_token(user_id)
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key,
            "Authorization": f"Bearer {token}"
        }

        payload: Dict[str, Any] = {}
        if title is not None:
            payload["title"] = title
        if description is not None:
            payload["description"] = description
        if start_time is not None:
            payload["start_time"] = start_time
        if end_time is not None:
            payload["end_time"] = end_time
        if duration_minutes is not None:
            payload["duration_minutes"] = duration_minutes
        if priority is not None:
            payload["priority"] = priority
        if status is not None:
            payload["status"] = status

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.put(
                f"{self.base_url}/tasks/{task_id}",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()

    async def get_task_statistics(self, user_id: int) -> Dict[str, Any]:
        """Get task statistics overview via GET /tasks/stats/overview."""
        token = await self._get_user_token(user_id)
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key,
            "Authorization": f"Bearer {token}"
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/tasks/stats/overview",
                headers=headers
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
