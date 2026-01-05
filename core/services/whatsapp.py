import requests
from typing import Optional, List, Dict, Any
from django.conf import settings


class WhatsAppService:
    """Service for interacting with WhatsApp-bridged rooms via Matrix."""

    def __init__(self, access_token: str):
        self.access_token = access_token
        self.homeserver = settings.MATRIX_CONFIG['HOMESERVER']

    def list_rooms(self, **kwargs) -> List[Dict[str, Any]]:
        """
        List all WhatsApp-bridged rooms with optional filtering.

        Fetches all rooms from Matrix with pagination (handles next_batch)
        and filters by provided kwargs on the Python side.

        Args:
            **kwargs: Filter criteria (e.g., creator="@user:matrix.org")
                      Each kwarg key should match a room field name.

        Returns:
            List of room data dictionaries
        """
        rooms: List[Dict[str, Any]] = []
        next_batch: Optional[str] = None
        limit = 100

        while True:
            url = f"{self.homeserver}/_synapse/admin/v1/rooms"
            params = {"limit": limit}

            if next_batch:
                params["from"] = next_batch

            headers = {"Authorization": f"Bearer {self.access_token}"}

            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()

            data = response.json()
            room_list = data.get('rooms', [])

            for room in room_list:
                if all(room.get(key) == value for key, value in kwargs.items()):
                    rooms.append(room)

            next_batch = data.get('next_batch')
            if not next_batch:
                break

        return rooms
