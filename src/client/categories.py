"""HTTP client for category-related endpoints."""

from typing import Dict, Any, List, Optional
from .base import BaseClient


class CategoryClient(BaseClient):
    """Client for category management endpoints."""

    async def get_categories(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Get all categories for a user.

        Args:
            user_id: User ID to fetch categories for

        Returns:
            List of category dictionaries with fields:
            - category_id: int
            - name: str
            - description: str
            - user_id: int
        """
        token = await self._get_user_token(user_id)
        return await self._get("/categories", token)

    async def create_category(
        self,
        user_id: int,
        name: str,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new category.

        Args:
            user_id: User ID to create category for
            name: Category name
            description: Optional category description

        Returns:
            Created category dictionary
        """
        token = await self._get_user_token(user_id)
        data = {"name": name}
        if description:
            data["description"] = description

        return await self._post("/categories", token, json=data)

    async def update_category(
        self,
        user_id: int,
        category_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update an existing category.

        Args:
            user_id: User ID
            category_id: Category ID to update
            name: New category name (optional)
            description: New description (optional)

        Returns:
            Updated category dictionary
        """
        token = await self._get_user_token(user_id)
        data = {}
        if name is not None:
            data["name"] = name
        if description is not None:
            data["description"] = description

        return await self._put(f"/categories/{category_id}", token, json=data)


# Global client instance
category_client = CategoryClient()
