import json
import requests
from datetime import datetime
from typing import List, Dict, Any, Optional

from django.conf import settings
from django.utils import timezone

from core.models import GeneralSettings, TodoList
from core.services.user import UserService


class LLMService:
    """Service for LLM-related operations."""

    NANOGPT_URL = "https://nano-gpt.com/api/v1/chat/completions"

    def __init__(self):
        self.actor_id = settings.MATRIX_CONFIG["USERNAME"]
        self.api_key = settings.OPENAI_CONFIG["API_KEY"]

    def get_model(self):
        settings = GeneralSettings.objects.all().first()
        return settings.llm_model

    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process LLM context and get a response from NanoGPT.

        Args:
            context: LLMContextResponse dict with messages, sender_mapping, goals, etc.

        Returns:
            Dict with room, summary, reply, needs_more_information, todo_list
        """
        model = self.get_model()
        room = context.get("room", {})
        prompt = f"""You are an assistant analyzing a conversation. Here is the context:

{json.dumps(context, indent=2)}

IMPORTANT: When referring to senders in your response, you MUST use the names from sender_mapping.
- If sender_mapping shows a user mapped to "yourself", that is the owner/actor - refer to them as "kamu" or "you"
- Other senders are mapped to their displayname - use these names directly in your response
- Never use generic terms like "Pengirim", "Sender", or raw user IDs

Based on the context above, provide a response following the output_format specified in the context.
Return ONLY valid JSON matching the output_format, no additional text."""

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
        }

        response = requests.post(self.NANOGPT_URL, headers=headers, json=payload)
        response.raise_for_status()

        data = response.json()
        content = data["choices"][0]["message"]["content"]

        try:
            start_idx = content.find("{")
            end_idx = content.rfind("}") + 1
            if start_idx != -1 and end_idx > start_idx:
                result = json.loads(content[start_idx:end_idx])
                result["room"] = room
                return result
        except (json.JSONDecodeError, ValueError):
            pass

        return {
            "room": room,
            "summary": content,
            "reply": None,
            "needs_more_information": False,
            "todo_list": [],
        }

    def _get_displayname(self, user_id: str, user_service: UserService) -> str:
        """
        Fetch displayname for a user from Matrix API.

        Args:
            user_id: The Matrix user ID
            user_service: UserService instance

        Returns:
            Displayname if available, else empty string
        """
        try:
            user_info = user_service.get_user_info(user_id)
            return user_info.get("displayname", "")
        except Exception:
            return ""

    def build_context(
        self,
        room: Dict[str, str],
        messages: List[Dict[str, str]],
        yourself: str,
        access_token: str,
        previous_messages: Dict[str, Any] = None,
        pending_todos: List[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Build LLM context from a list of messages.

        Args:
            room: Dict with 'id', 'name', and 'platform' keys
            messages: List of dicts with 'sender' and 'content' keys
            yourself: The user_id that represents "yourself"
            access_token: Matrix access token for fetching user info
            previous_messages: Dict with 'summary' and 'todo_list' from last LLM reply
            pending_todos: List of pending todo items with id, description, notes

        Returns:
            Complete LLM context dictionary
        """
        user_service = UserService(access_token=access_token)
        sender_mapping = {yourself: "yourself"}

        for msg in messages:
            sender = msg.get("sender", "")
            if sender and sender not in sender_mapping:
                displayname = self._get_displayname(sender, user_service)
                sender_mapping[sender] = displayname if displayname else sender

        return {
            "room": room,
            "messages": [
                {"sender": m["sender"], "content": m["content"]} for m in messages
            ],
            "previous_messages": previous_messages
            or {"summary": None, "todo_list": None},
            "pending_todos": pending_todos or [],
            "sender_mapping": sender_mapping,
            "goals": {
                "reply_generation": {
                    "direct_answer_if_possible": True,
                    "acknowledge_if_unclear": True,
                },
                "task_extraction": {
                    "enabled": True,
                    "only_if_actionable": True,
                },
                "todo_management": {
                    "enabled": True,
                    "check_existing_todos": True,
                    "create_new_todos": True,
                },
                "conversation_summary": {
                    "enabled": True,
                    "length": "short",
                },
            },
            "response_rules": {
                "language": "same as sender",
                "tone": "natural, polite, concise",
                "emoji_usage": "only_if_user_used",
                "no_markdown": True,
            },
            "output_format": {
                "room": "object with id, name, platform",
                "summary": "string",
                "reply": "string | null",
                "needs_more_information": "boolean",
                "todo_updates": [
                    {
                        "id": "existing todo id (required for updates)",
                        "status": "done | cancelled | pending",
                        "notes": "optional additional notes",
                    }
                ],
                "new_todos": ["array of new todo descriptions to create"],
            },
        }

    def build_llm_context_for_summary(
        self, state, room_service, access_token: str
    ) -> Optional[Dict[str, Any]]:
        """
        Build LLM context for generating a room summary.

        Args:
            state: ConversationProcessingState for the room
            room_service: RoomService instance for fetching messages
            access_token: Matrix access token

        Returns:
            LLM context dict or None if no messages to process
        """
        from core.models import RoomSummary

        room = state.room
        from_timestamp = state.last_message_synced_at

        # Fetch messages from Matrix
        messages_data = room_service.get_messages(
            room_id=room.room_id,
            room_name=room.room_name or room.room_id,
            access_token=access_token,
            from_timestamp=from_timestamp,
        )

        messages = messages_data.get("messages", [])

        if not messages:
            return None

        # Get last RoomSummary for previous_messages context
        last_summary = RoomSummary.objects.filter(room=room).first()
        previous_messages = None
        if last_summary:
            previous_messages = {
                "summary": last_summary.summary,
                "todo_list": last_summary.todo_list,
            }

        # Get pending todos for this room
        pending_todos = list(
            TodoList.objects.filter(
                room=room,
                status=TodoList.STATUS_PENDING,
            ).values("id", "description", "notes")
        )

        # Build LLM context
        room_info = {
            "id": room.room_id,
            "name": room.room_name or room.room_id,
            "platform": room.platform,
        }
        formatted_messages = [
            {"sender": m["sender"], "content": m["body"]} for m in messages
        ]

        # Use subscriber's matrix_id as "yourself" for sender mapping
        subscriber_matrix_id = room.subscriber.matrix_id

        context = self.build_context(
            room=room_info,
            messages=formatted_messages,
            yourself=subscriber_matrix_id,
            access_token=access_token,
            previous_messages=previous_messages,
            pending_todos=pending_todos,
        )

        # Add metadata for processing
        context["_metadata"] = {
            "message_count": len(messages),
            "from_timestamp": from_timestamp.isoformat() if from_timestamp else None,
            "to_timestamp": messages[-1].get("timestamp") if messages else None,
        }

        return context

    def process_room(self, state, context: Dict[str, Any]):
        """
        Process room with LLM and save the summary.

        Args:
            state: ConversationProcessingState for the room
            context: LLM context dict from build_context_for_room

        Returns:
            The created RoomSummary
        """
        from core.models import (
            ConversationProcessingState,
            RoomSummary,
        )

        room = state.room
        now = timezone.now()

        # Extract metadata
        metadata = context.pop("_metadata", {})
        message_count = metadata.get("message_count", 0)
        from_timestamp_str = metadata.get("from_timestamp")
        to_timestamp_str = metadata.get("to_timestamp")

        from_timestamp = None
        if from_timestamp_str:
            from_timestamp = datetime.fromisoformat(from_timestamp_str)

        to_timestamp = now
        if to_timestamp_str:
            to_timestamp = datetime.fromisoformat(to_timestamp_str)

        # Process with LLM
        result = self.process(context=context)

        # Handle todo updates from LLM response
        todo_updates = result.get("todo_updates", [])
        for update in todo_updates:
            todo_id = update.get("id")
            if not todo_id:
                continue
            try:
                todo = TodoList.objects.get(id=todo_id, room=room)
                new_status = update.get("status")
                if new_status in [TodoList.STATUS_DONE, TodoList.STATUS_CANCELLED, TodoList.STATUS_PENDING]:
                    todo.status = new_status
                if update.get("notes"):
                    if todo.notes:
                        todo.notes = f"{todo.notes}\n{update['notes']}"
                    else:
                        todo.notes = update["notes"]
                todo.save()
            except TodoList.DoesNotExist:
                pass

        # Create new todos from LLM response
        new_todos = result.get("new_todos", [])
        for description in new_todos:
            if description and isinstance(description, str):
                TodoList.objects.create(
                    room=room,
                    description=description,
                    status=TodoList.STATUS_PENDING,
                )

        # Save RoomSummary (without old todo_list field, use new_todos for reference)
        summary = RoomSummary.objects.create(
            room=room,
            summary=result.get("summary", ""),
            reply=result.get("reply"),
            needs_more_information=result.get("needs_more_information", False),
            todo_list=new_todos,
            message_count=message_count,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
        )

        # Update ConversationProcessingState
        state.status = ConversationProcessingState.STATUS_IDLE
        state.last_message_synced_at = to_timestamp
        state.last_summarized_at = now
        state.llm_context_to_process = None
        state.failure_reason = ""
        state.save(
            update_fields=[
                "status",
                "last_message_synced_at",
                "last_summarized_at",
                "llm_context_to_process",
                "failure_reason",
                "updated_at",
            ]
        )

        return summary

    def format_summary_message(self, summary, question_count: int = 0) -> str:
        """
        Format summary as human-readable multiline text.

        Args:
            summary: RoomSummary instance
            question_count: Current daily question/summary count

        Returns:
            Formatted message string
        """
        room = summary.room
        lines = [
            f"Room: {room.room_name or room.room_id}",
            f"Platform: {room.platform}",
            "",
            "--- Summary ---",
            "",
            summary.summary,
        ]

        if summary.reply:
            lines.extend(
                [
                    "",
                    "--- Suggested Reply ---",
                    "",
                    summary.reply,
                ]
            )

        if summary.needs_more_information:
            lines.extend(
                [
                    "",
                    "[Needs more information]",
                ]
            )

        # Show new action items created from this summary
        if summary.todo_list:
            lines.extend(
                [
                    "",
                    "--- New Action Items ---",
                ]
            )
            for i, item in enumerate(summary.todo_list, 1):
                lines.append(f"{i}. {item}")

        # Show all pending todos for this room
        pending_todos = TodoList.objects.filter(
            room=room,
            status=TodoList.STATUS_PENDING,
        ).order_by("created_at")

        if pending_todos.exists():
            lines.extend(
                [
                    "",
                    "--- Pending Todos ---",
                ]
            )
            for todo in pending_todos:
                lines.append(f"[{todo.id}] {todo.description}")

        lines.extend(
            [
                "",
                f"Messages processed: {summary.message_count}",
                f"You have asked {question_count} question(s) today",
            ]
        )

        return "\n".join(lines)
