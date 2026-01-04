import requests
import urllib.parse
from typing import Optional, List, Dict, Any
from datetime import datetime
from django.conf import settings
from django.utils import timezone


class MatrixService:
    """Service for interacting with Matrix/Synapse APIs."""

    def __init__(self):
        self.homeserver = settings.MATRIX_CONFIG['HOMESERVER']
        self.username = settings.MATRIX_CONFIG['USERNAME']
        self.password = settings.MATRIX_CONFIG['PASSWORD']
        self._access_token: Optional[str] = None

    def login(self, username: Optional[str] = None, password: Optional[str] = None) -> Dict[str, Any]:
        """
        Login to Matrix homeserver and get access token.

        Args:
            username: Matrix username (defaults to config)
            password: Matrix password (defaults to config)

        Returns:
            Login response with access_token, user_id, device_id
        """
        url = f"{self.homeserver}/_matrix/client/v3/login"

        payload = {
            "type": "m.login.password",
            "identifier": {
                "type": "m.id.user",
                "user": username or self.username,
            },
            "password": password or self.password,
        }

        response = requests.post(url, json=payload)
        response.raise_for_status()

        data = response.json()
        self._access_token = data.get('access_token')

        return data

    def get_access_token(self) -> str:
        """Get current access token, logging in if necessary."""
        if not self._access_token:
            self.login()
        return self._access_token

    def fetch_all_rooms(self, access_token: Optional[str] = None, target_creator: str = "@friday:matrix.tirta.me") -> List[Dict[str, Any]]:
        """
        Fetch all rooms from Synapse admin API with pagination.

        Only returns rooms where creator matches target_creator.

        Args:
            access_token: Matrix access token (uses cached if not provided)
            target_creator: Only return rooms created by this user

        Returns:
            List of room data dictionaries
        """
        token = access_token or self.get_access_token()
        rooms = []
        next_batch: Optional[str] = None
        limit = 100

        while True:
            url = f"{self.homeserver}/_synapse/admin/v1/rooms"
            params = {"limit": limit}

            if next_batch:
                params["from"] = next_batch

            headers = {"Authorization": f"Bearer {token}"}

            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()

            data = response.json()
            room_list = data.get('rooms', [])

            for room in room_list:
                creator = room.get('creator', '')
                if creator == target_creator:
                    rooms.append(room)

            next_batch = data.get('next_batch')
            if not next_batch:
                break

        return rooms

    def get_room_details(self, room_id: str, access_token: Optional[str] = None) -> Dict[str, Any]:
        """
        Get detailed information about a specific room.

        Args:
            room_id: The Matrix room ID
            access_token: Matrix access token (uses cached if not provided)

        Returns:
            Room details dictionary
        """
        token = access_token or self.get_access_token()
        url = f"{self.homeserver}/_synapse/admin/v1/rooms/{room_id}"
        headers = {"Authorization": f"Bearer {token}"}

        response = requests.get(url, headers=headers)
        response.raise_for_status()

        return response.json()

    def fetch_room_messages(
        self,
        room_id: str,
        from_timestamp: Optional[datetime] = None,
        limit: int = 1000,
        access_token: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch messages from a Matrix room.

        Uses the Matrix Client API to retrieve room messages.
        If from_timestamp is provided, only fetches messages after that time.

        Args:
            room_id: The Matrix room ID (e.g., "!abc123:matrix.org")
            from_timestamp: Only fetch messages after this timestamp
            limit: Maximum number of messages to fetch
            access_token: Matrix access token (uses cached if not provided)

        Returns:
            List of message events with sender, content, timestamp
        """
        token = access_token or self.get_access_token()

        # URL encode the room_id since it contains special characters
        encoded_room_id = urllib.parse.quote(room_id)

        url = f"{self.homeserver}/_matrix/client/v3/rooms/{encoded_room_id}/messages"
        headers = {"Authorization": f"Bearer {token}"}

        params = {
            "dir": "b",  # backward from the most recent
            "limit": limit,
        }

        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()

        data = response.json()
        events = data.get('chunk', [])

        # Filter to only message events (m.room.message)
        messages = []
        for event in events:
            if event.get('type') != 'm.room.message':
                continue

            # Get timestamp from event
            origin_ts = event.get('origin_server_ts', 0)
            event_time = datetime.fromtimestamp(origin_ts / 1000, tz=timezone.utc)

            # Filter by from_timestamp if provided
            if from_timestamp and event_time <= from_timestamp:
                continue

            content = event.get('content', {})
            messages.append({
                'sender': event.get('sender', ''),
                'body': content.get('body', ''),
                'msgtype': content.get('msgtype', ''),
                'timestamp': event_time.isoformat(),
                'event_id': event.get('event_id', ''),
            })

        # Reverse to chronological order (oldest first)
        messages.reverse()

        return messages
