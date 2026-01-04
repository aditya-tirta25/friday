import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from django.utils import timezone
from django.conf import settings
from openai import OpenAI

from core.models import Room, RoomCheckLog
from core.services.matrix_service import MatrixService


class RoomService:
    """Service for room management and AI-powered summaries."""

    def __init__(self):
        self.openai_client = OpenAI(
            api_key=settings.OPENAI_CONFIG['API_KEY'],
            base_url=settings.OPENAI_CONFIG['BASE_URL'],
        )
        self.model = "gpt-4o-mini"  # Cost-effective, good for summarization

    def sync_rooms(self, rooms_data: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Sync rooms from Matrix API to database.

        Creates new rooms or updates existing ones, marking all as unchecked.

        Args:
            rooms_data: List of room data from Matrix API

        Returns:
            Dictionary with synced_count, new_rooms, updated_rooms
        """
        new_rooms = 0
        updated_rooms = 0

        for room_data in rooms_data:
            room_id = room_data.get('room_id')
            if not room_id:
                continue

            room_created_at = None
            if room_data.get('creation_ts'):
                room_created_at = datetime.fromtimestamp(
                    room_data['creation_ts'] / 1000,
                    tz=timezone.utc
                )

            room, created = Room.objects.update_or_create(
                room_id=room_id,
                defaults={
                    'name': room_data.get('name', ''),
                    'creator': room_data.get('creator', ''),
                    'member_count': room_data.get('joined_members', 0),
                    'room_created_at': room_created_at,
                    'is_checked': False,
                }
            )

            if created:
                new_rooms += 1
            else:
                updated_rooms += 1

        return {
            'synced_count': new_rooms + updated_rooms,
            'new_rooms': new_rooms,
            'updated_rooms': updated_rooms,
        }

    def get_unchecked_rooms(self) -> List[Room]:
        """Get all rooms that have not been checked."""
        return list(Room.objects.filter(is_checked=False).order_by('-created_at'))

    def get_all_rooms(self) -> List[Room]:
        """Get all rooms."""
        return list(Room.objects.all().order_by('-created_at'))

    def mark_as_checked(self, room_id: int, notes: Optional[str] = None) -> Room:
        """
        Mark a room as checked and create a check log.

        Args:
            room_id: Database ID of the room
            notes: Optional notes about the check

        Returns:
            Updated Room object
        """
        room = Room.objects.get(id=room_id)
        room.is_checked = True
        room.last_checked_at = timezone.now()
        room.save()

        RoomCheckLog.objects.create(
            room=room,
            notes=notes,
        )

        return room

    def generate_summary(self, rooms: List[Room]) -> Dict[str, Any]:
        """
        Generate an AI-powered summary of unchecked rooms.

        Args:
            rooms: List of Room objects to summarize

        Returns:
            Dictionary with summary text and todo list
        """
        if not rooms:
            return {
                'summary': 'No unchecked rooms to review.',
                'todo_list': []
            }

        room_info = []
        for room in rooms:
            room_info.append({
                'room_id': room.room_id,
                'name': room.name or 'Unnamed Room',
                'creator': room.creator,
                'member_count': room.member_count,
                'created_at': room.room_created_at.isoformat() if room.room_created_at else 'Unknown',
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
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        response_text = response.choices[0].message.content

        try:
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            if start_idx != -1 and end_idx > start_idx:
                json_str = response_text[start_idx:end_idx]
                result = json.loads(json_str)
                return result
        except (json.JSONDecodeError, ValueError):
            pass

        return {
            'summary': response_text,
            'todo_list': [
                {
                    'room_id': room.room_id,
                    'room_name': room.name or 'Unnamed',
                    'action': 'Review room',
                    'priority': 'medium'
                }
                for room in rooms
            ]
        }

    def generate_conversation_summary(
        self,
        room: Room,
        messages: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate an AI-powered summary of room conversation with action items.

        Args:
            room: Room model instance
            messages: List of message dictionaries from Matrix API

        Returns:
            Dictionary with summary text and action_items list
        """
        if not messages:
            return {
                'summary': 'No new messages to summarize.',
                'action_items': []
            }

        # Format messages for the prompt
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
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        response_text = response.choices[0].message.content

        # Parse JSON from response
        try:
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            if start_idx != -1 and end_idx > start_idx:
                json_str = response_text[start_idx:end_idx]
                result = json.loads(json_str)
                return result
        except (json.JSONDecodeError, ValueError):
            pass

        # Fallback if JSON parsing fails
        return {
            'summary': response_text,
            'action_items': []
        }

    def summarize_room_conversation(
        self,
        matrix_room_id: str,
        matrix_service: MatrixService
    ) -> Dict[str, Any]:
        """
        Full workflow: fetch messages, generate summary, store in database.

        Args:
            matrix_room_id: The Matrix room ID string
            matrix_service: MatrixService instance for API calls

        Returns:
            Dictionary with room, summary, action_items, check_log_id, etc.
        """
        # Get room from database
        try:
            room = Room.objects.get(room_id=matrix_room_id)
        except Room.DoesNotExist:
            raise ValueError(f"Room not found in database: {matrix_room_id}")

        # Determine from_timestamp
        from_timestamp = room.last_checked_at  # Can be None

        # Fetch messages from Matrix
        messages = matrix_service.fetch_room_messages(
            room_id=matrix_room_id,
            from_timestamp=from_timestamp
        )

        # Generate AI summary
        summary_data = self.generate_conversation_summary(room, messages)

        # Update room and create check log
        now = timezone.now()
        room.is_checked = True
        room.last_checked_at = now
        room.save()

        check_log = RoomCheckLog.objects.create(
            room=room,
            summary=summary_data.get('summary', ''),
            notes=json.dumps(summary_data.get('action_items', []))
        )

        return {
            'room': room,
            'summary': summary_data.get('summary', ''),
            'action_items': summary_data.get('action_items', []),
            'message_count': len(messages),
            'from_timestamp': from_timestamp,
            'to_timestamp': now,
            'check_log_id': check_log.id,
        }
