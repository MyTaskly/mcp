"""HTTP client for task-related endpoints."""

from typing import Dict, Any, List, Optional
from .base import BaseClient

# Mapping per normalizzare i valori di stato (inglese/case-insensitive → italiano)
_STATO_ALIASES: dict[str, str] = {
    "pending": "In sospeso",
    "in progress": "In sospeso",
    "in_progress": "In sospeso",
    "open": "In sospeso",
    "todo": "In sospeso",
    "completed": "Completato",
    "complete": "Completato",
    "done": "Completato",
    "finished": "Completato",
    "cancelled": "Annullato",
    "canceled": "Annullato",
    "cancel": "Annullato",
    "abandoned": "Annullato",
    "in sospeso": "In sospeso",
    "sospeso": "In sospeso",
    "completato": "Completato",
    "annullato": "Annullato",
}

# Mapping per normalizzare i valori di priorità
_PRIORITA_ALIASES: dict[str, str] = {
    "low": "Bassa",
    "medium": "Media",
    "normal": "Media",
    "high": "Alta",
    "critical": "Alta",
    "urgent": "Alta",
    "bassa": "Bassa",
    "media": "Media",
    "alta": "Alta",
}


def _normalize_status(value: Optional[str]) -> Optional[str]:
    """Normalizza un valore di stato a quello atteso dall'API."""
    if value is None:
        return None
    return _STATO_ALIASES.get(value.lower().strip(), value)


def _normalize_priority(value: Optional[str]) -> Optional[str]:
    """Normalizza un valore di priorità a quello atteso dall'API."""
    if value is None:
        return None
    return _PRIORITA_ALIASES.get(value.lower().strip(), value)


class TaskClient(BaseClient):
    """Client for task management endpoints."""

    async def get_tasks(
        self,
        user_id: int,
        category_id: Optional[int] = None,
        priority: Optional[str] = None,
        status: Optional[str] = None,
        task_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get tasks for a user with optional filters.

        Args:
            user_id: User ID to fetch tasks for
            category_id: Filter by category ID (optional)
            priority: Filter by priority: "Alta", "Media", "Bassa" (optional)
            status: Filter by status: "In sospeso", "Completato", "Annullato" (optional)
            task_id: Get specific task by ID (optional)

        Returns:
            List of task dictionaries
        """
        token = await self._get_user_token(user_id)
        params = {}
        if category_id is not None:
            params["category_id"] = category_id
        if priority is not None:
            params["priority"] = priority
        if status is not None:
            params["status"] = status
        if task_id is not None:
            params["task_id"] = task_id

        return await self._get("/tasks/", token, params=params)

    async def create_task(
        self,
        user_id: int,
        title: str,
        category_id: int,
        end_time: Optional[str] = None,
        start_time: Optional[str] = None,
        description: Optional[str] = None,
        priority: str = "Bassa"
    ) -> Dict[str, Any]:
        """
        Create a new task.

        Args:
            user_id: User ID
            title: Task title (max 100 characters)
            category_id: Category ID (required)
            end_time: End date/time (format: YYYY-MM-DD HH:MM:SS)
            start_time: Start date/time (optional)
            description: Task description
            priority: "Alta", "Media", or "Bassa" (default: "Bassa")

        Returns:
            Created task dictionary
        """
        token = await self._get_user_token(user_id)
        data = {
            "user": str(user_id),  # FastAPI schema requires 'user' field
            "title": title,
            "description": description if description else "",  # Always send description (FastAPI requires it)
            "category_id": category_id,
            "priority": _normalize_priority(priority),
            "status": "In sospeso"
        }
        if end_time:
            data["end_time"] = end_time
        if start_time:
            data["start_time"] = start_time

        return await self._post("/tasks", token, json=data)

    async def update_task(
        self,
        user_id: int,
        task_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        priority: Optional[str] = None,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update an existing task.

        Args:
            user_id: User ID
            task_id: Task ID to update
            title: New title (optional)
            description: New description (optional)
            start_time: New start time (optional)
            end_time: New end time (optional)
            priority: New priority (optional)
            status: New status (optional)

        Returns:
            Updated task dictionary
        """
        token = await self._get_user_token(user_id)
        data = {}
        if title is not None:
            data["title"] = title
        if description is not None:
            data["description"] = description
        if start_time is not None:
            data["start_time"] = start_time
        if end_time is not None:
            data["end_time"] = end_time
        if priority is not None:
            data["priority"] = _normalize_priority(priority)
        if status is not None:
            data["status"] = _normalize_status(status)

        return await self._put(f"/tasks/{task_id}", token, json=data)

    async def delete_task(self, user_id: int, task_id: int) -> Dict[str, Any]:
        """
        Delete a task.

        Args:
            user_id: User ID
            task_id: Task ID to delete

        Returns:
            Deletion confirmation
        """
        token = await self._get_user_token(user_id)
        return await self._delete(f"/tasks/{task_id}", token)

    async def get_task_statistics(self, user_id: int) -> Dict[str, Any]:
        """
        Get task statistics for a user.

        Args:
            user_id: User ID

        Returns:
            Statistics dictionary with counts by status, priority, category
        """
        token = await self._get_user_token(user_id)
        return await self._get("/tasks/statistics", token)


# Global client instance
task_client = TaskClient()
