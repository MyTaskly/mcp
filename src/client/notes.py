"""HTTP client for note-related endpoints."""

from typing import Dict, Any, List, Optional
from .base import BaseClient


class NoteClient(BaseClient):
    """Client for note management endpoints."""

    async def get_notes(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Get all notes for a user.

        Args:
            user_id: User ID to fetch notes for

        Returns:
            List of note dictionaries with fields:
            - note_id: int
            - title: str
            - position_x: str
            - position_y: str
            - color: str
            - created_at: str
        """
        token = await self._get_user_token(user_id)
        return await self._get("/notes", token)

    async def create_note(
        self,
        user_id: int,
        title: str,
        position_x: str = "0",
        position_y: str = "0",
        color: str = "#FFEB3B"
    ) -> Dict[str, Any]:
        """
        Create a new note.

        Args:
            user_id: User ID
            title: Note text content (unlimited length)
            position_x: X position on canvas (default: "0")
            position_y: Y position on canvas (default: "0")
            color: Note color in hex format (default: "#FFEB3B" yellow)

        Returns:
            Created note dictionary
        """
        token = await self._get_user_token(user_id)
        data = {
            "user_id": user_id,
            "title": title,
            "position_x": position_x,
            "position_y": position_y,
            "color": color
        }
        result = await self._post("/notes", token, json=data)

        # FastAPI returns {"note_id": ..., "status_code": 201}
        # Transform to expected format
        return {
            "note_id": result.get("note_id"),
            "title": title,
            "color": color,
            "position_x": position_x,
            "position_y": position_y
        }

    async def update_note(
        self,
        user_id: int,
        note_id: int,
        title: Optional[str] = None,
        position_x: Optional[str] = None,
        position_y: Optional[str] = None,
        color: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update an existing note.

        Args:
            user_id: User ID
            note_id: Note ID to update
            title: New note text (optional)
            position_x: New X position (optional)
            position_y: New Y position (optional)
            color: New color (optional)

        Returns:
            Updated note dictionary
        """
        token = await self._get_user_token(user_id)
        data = {}
        if title is not None:
            data["title"] = title
        if position_x is not None:
            data["position_x"] = position_x
        if position_y is not None:
            data["position_y"] = position_y
        if color is not None:
            data["color"] = color

        return await self._put(f"/notes/{note_id}", token, json=data)

    async def delete_note(self, user_id: int, note_id: int) -> Dict[str, Any]:
        """
        Delete a note.

        Args:
            user_id: User ID
            note_id: Note ID to delete

        Returns:
            Deletion confirmation
        """
        token = await self._get_user_token(user_id)
        return await self._delete(f"/notes/{note_id}", token)


# Global client instance
note_client = NoteClient()
