import requests
import urllib.parse
from typing import Dict, Any
from django.conf import settings


class UserService:
    """Service for fetching user information from Matrix."""

    def __init__(self, access_token: str):
        self.access_token = access_token
        self.homeserver = settings.MATRIX_CONFIG["HOMESERVER"]

    def get_user_info(self, user_id: str) -> Dict[str, Any]:
        """
        Fetch user information from Synapse Admin API.

        Args:
            user_id: The Matrix user ID (e.g., "@user:matrix.org")

        Returns:
            User information dict from Matrix API
        """
        encoded_user_id = urllib.parse.quote(user_id)
        url = f"{self.homeserver}/_synapse/admin/v2/users/{encoded_user_id}"
        headers = {"Authorization": f"Bearer {self.access_token}"}

        response = requests.get(url, headers=headers)
        response.raise_for_status()

        return response.json()
