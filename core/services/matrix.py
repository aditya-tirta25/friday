import json
import requests
import urllib.parse
import uuid
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from openai import OpenAI

from core.models import (
    Room,
    RoomCheckLog,
    ConversationProcessingState,
    RoomDailySummaryCount,
    SubscriberRoom,
    Subscription,
)


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

    def send_message(
        self,
        room_id: str,
        body: str,
        msgtype: str = "m.text",
        access_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send a message to a Matrix room.

        Args:
            room_id: The Matrix room ID
            body: The message body
            msgtype: Message type (default: m.text)
            access_token: Matrix access token (uses cached if not provided)

        Returns:
            Response with event_id
        """
        token = access_token or self.get_access_token()
        encoded_room_id = urllib.parse.quote(room_id)
        txn_id = str(uuid.uuid4())

        url = f"{self.homeserver}/_matrix/client/v3/rooms/{encoded_room_id}/send/m.room.message/{txn_id}"
        headers = {"Authorization": f"Bearer {token}"}

        payload = {
            "msgtype": msgtype,
            "body": body,
        }

        response = requests.put(url, headers=headers, json=payload)
        response.raise_for_status()

        return response.json()

    def get_last_message(
        self, room_id: str, access_token: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get the last message from a Matrix room.

        Args:
            room_id: The Matrix room ID
            access_token: Matrix access token (uses cached if not provided)

        Returns:
            Dict with sender, body, timestamp, event_id or None if no messages
        """
        messages = self.fetch_room_messages(
            room_id=room_id,
            limit=10,
            access_token=access_token,
        )

        if messages:
            # Messages are in chronological order, last one is most recent
            return messages[-1]
        return None

    def get_active_subscribers(self) -> List:
        """
        Get all active subscribers with valid subscriptions.

        Returns:
            List of Subscriber objects with active subscriptions and matrix_room_id
        """
        from core.models import Subscriber

        active_subscriber_ids = Subscription.objects.filter(
            status="active"
        ).values_list("subscriber_id", flat=True)

        return list(
            Subscriber.objects.filter(
                id__in=active_subscriber_ids,
                is_active=True,
                matrix_room_id__isnull=False,
            ).exclude(matrix_room_id="")
        )

class RoomService:
    """Service for room management and AI-powered summaries."""

    def __init__(self):
        self.openai_client = OpenAI(
            api_key=settings.OPENAI_CONFIG["API_KEY"],
            base_url=settings.OPENAI_CONFIG["BASE_URL"],
        )
        self.model = "gpt-4o-mini"

    def sync_rooms(self, rooms_data: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Sync rooms from Matrix API to database.

        Creates new rooms or updates existing ones, marking all as unchecked.
        """
        new_rooms = 0
        updated_rooms = 0

        for room_data in rooms_data:
            room_id = room_data.get("room_id")
            if not room_id:
                continue

            room_created_at = None
            if room_data.get("creation_ts"):
                room_created_at = datetime.fromtimestamp(
                    room_data["creation_ts"] / 1000, tz=timezone.utc
                )

            room, created = Room.objects.update_or_create(
                room_id=room_id,
                defaults={
                    "name": room_data.get("name", ""),
                    "creator": room_data.get("creator", ""),
                    "member_count": room_data.get("joined_members", 0),
                    "room_created_at": room_created_at,
                    "is_checked": False,
                },
            )

            if created:
                new_rooms += 1
            else:
                updated_rooms += 1

        return {
            "synced_count": new_rooms + updated_rooms,
            "new_rooms": new_rooms,
            "updated_rooms": updated_rooms,
        }

    def get_unchecked_rooms(self) -> List[Room]:
        """Get all rooms that have not been checked."""
        return list(Room.objects.filter(is_checked=False).order_by("-created_at"))

    def get_all_rooms(self) -> List[Room]:
        """Get all rooms."""
        return list(Room.objects.all().order_by("-created_at"))

    def get_messages(
        self,
        room_id: str,
        room_name: str,
        access_token: str,
        limit: int = 100,
        from_timestamp: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Fetch messages from a Matrix room using Synapse Admin API.
        Filters messages after from_timestamp if provided.
        """
        homeserver = settings.MATRIX_CONFIG["HOMESERVER"]
        encoded_room_id = urllib.parse.quote(room_id)
        headers = {"Authorization": f"Bearer {access_token}"}

        url = f"{homeserver}/_synapse/admin/v1/rooms/{encoded_room_id}/messages"
        params = {"limit": limit, "dir": "b"}

        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()

        data = response.json()
        chunk = data.get("chunk", [])

        messages = []
        for event in chunk:
            if event.get("type") != "m.room.message":
                continue

            origin_ts = event.get("origin_server_ts", 0)
            event_time = datetime.fromtimestamp(origin_ts / 1000, tz=timezone.utc)

            # Filter by from_timestamp if provided
            if from_timestamp and event_time <= from_timestamp:
                continue

            content = event.get("content", {})

            messages.append({
                "sender": event.get("sender", ""),
                "body": content.get("body", ""),
                "msgtype": content.get("msgtype", ""),
                "timestamp": event_time.isoformat(),
                "event_id": event.get("event_id", ""),
            })

        messages.reverse()
        return {
            "room": {"id": room_id, "name": room_name},
            "messages": messages,
            "total": len(messages),
        }

    def mark_as_checked(self, room_id: int, notes: Optional[str] = None) -> Room:
        """Mark a room as checked and create a check log."""
        room = Room.objects.get(id=room_id)
        room.is_checked = True
        room.last_checked_at = timezone.now()
        room.save()

        RoomCheckLog.objects.create(room=room, notes=notes)
        return room

    def generate_summary(self, rooms: List[Room]) -> Dict[str, Any]:
        """Generate an AI-powered summary of unchecked rooms."""
        if not rooms:
            return {"summary": "No unchecked rooms to review.", "todo_list": []}

        room_info = []
        for room in rooms:
            room_info.append({
                "room_id": room.room_id,
                "name": room.name or "Unnamed Room",
                "creator": room.creator,
                "member_count": room.member_count,
                "created_at": (
                    room.room_created_at.isoformat()
                    if room.room_created_at
                    else "Unknown"
                ),
            })

        prompt = f"""You are an assistant helping to manage Matrix chat rooms.
Analyze the following list of unchecked rooms and provide:
1. A brief summary of the rooms (2-3 sentences)
2. A prioritized todo list of actions that need to be taken for each room

Rooms to analyze:
{json.dumps(room_info, indent=2)}

Respond in JSON format with the following structure:
{{
    "summary": "Your summary here",
    "todo_list": [
        {{
            "room_id": "!roomid:matrix.org",
            "room_name": "Room Name",
            "action": "What needs to be done",
            "priority": "high|medium|low"
        }}
    ]
}}

Focus on identifying rooms that might need immediate attention (many members, old unchecked, etc.)."""

        response = self.openai_client.chat.completions.create(
            model=self.model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )

        response_text = response.choices[0].message.content

        try:
            start_idx = response_text.find("{")
            end_idx = response_text.rfind("}") + 1
            if start_idx != -1 and end_idx > start_idx:
                json_str = response_text[start_idx:end_idx]
                result = json.loads(json_str)
                return result
        except (json.JSONDecodeError, ValueError):
            pass

        return {
            "summary": response_text,
            "todo_list": [
                {
                    "room_id": room.room_id,
                    "room_name": room.name or "Unnamed",
                    "action": "Review room",
                    "priority": "medium",
                }
                for room in rooms
            ],
        }

    def generate_conversation_summary(
        self, room: Room, messages: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate an AI-powered summary of room conversation with action items."""
        if not messages:
            return {"summary": "No new messages to summarize.", "action_items": []}

        formatted_messages = []
        for msg in messages:
            formatted_messages.append(
                f"[{msg['timestamp']}] {msg['sender']}: {msg['body']}"
            )

        conversation_text = "\n".join(formatted_messages)

        prompt = f"""You are an assistant analyzing a Matrix chat room conversation.
Room: {room.name or room.room_id}

Analyze the following conversation and provide:
1. A concise summary of the discussion (3-5 sentences)
2. A list of action items that were mentioned or implied

Conversation:
{conversation_text}

Respond in JSON format:
{{
    "summary": "Your summary of the conversation here",
    "action_items": [
        {{
            "description": "What needs to be done",
            "assignee": "@user:matrix.org or null if not specified",
            "due_date": "mentioned deadline or null",
            "priority": "high|medium|low"
        }}
    ]
}}

Focus on:
- Key decisions made
- Questions that need answers
- Tasks assigned to specific people
- Deadlines mentioned
- Unresolved issues"""

        response = self.openai_client.chat.completions.create(
            model=self.model,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )

        response_text = response.choices[0].message.content

        try:
            start_idx = response_text.find("{")
            end_idx = response_text.rfind("}") + 1
            if start_idx != -1 and end_idx > start_idx:
                json_str = response_text[start_idx:end_idx]
                result = json.loads(json_str)
                return result
        except (json.JSONDecodeError, ValueError):
            pass

        return {"summary": response_text, "action_items": []}

    def summarize_room_conversation(
        self, matrix_room_id: str, matrix_service: MatrixService
    ) -> Dict[str, Any]:
        """Full workflow: fetch messages, generate summary, store in database."""
        try:
            room = Room.objects.get(room_id=matrix_room_id)
        except Room.DoesNotExist:
            raise ValueError(f"Room not found in database: {matrix_room_id}")

        from_timestamp = room.last_checked_at

        messages = matrix_service.fetch_room_messages(
            room_id=matrix_room_id, from_timestamp=from_timestamp
        )

        summary_data = self.generate_conversation_summary(room, messages)

        now = timezone.now()
        room.is_checked = True
        room.last_checked_at = now
        room.save()

        check_log = RoomCheckLog.objects.create(
            room=room,
            summary=summary_data.get("summary", ""),
            notes=json.dumps(summary_data.get("action_items", [])),
        )

        return {
            "room": room,
            "summary": summary_data.get("summary", ""),
            "action_items": summary_data.get("action_items", []),
            "message_count": len(messages),
            "from_timestamp": from_timestamp,
            "to_timestamp": now,
            "check_log_id": check_log.id,
        }
