import json
import requests
from typing import List, Dict, Any
from django.conf import settings

from core.services.user import UserService


class LLMService:
    """Service for LLM-related operations."""

    NANOGPT_URL = "https://nano-gpt.com/api/v1/chat/completions"

    def __init__(self):
        self.actor_id = settings.MATRIX_CONFIG["USERNAME"]
        self.api_key = settings.OPENAI_CONFIG["API_KEY"]

    def process(
        self, context: Dict[str, Any], model: str = "gpt-4o-mini"
    ) -> Dict[str, Any]:
        """
        Process LLM context and get a response from NanoGPT.

        Args:
            context: LLMContextResponse dict with messages, sender_mapping, goals, etc.
            model: Model to use for processing

        Returns:
            Dict with room, summary, reply, needs_more_information, todo_list
        """
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
    ) -> Dict[str, Any]:
        """
        Build LLM context from a list of messages.

        Args:
            room: Dict with 'id', 'name', and 'platform' keys
            messages: List of dicts with 'sender' and 'content' keys
            yourself: The user_id that represents "yourself"
            access_token: Matrix access token for fetching user info

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
                "todo_list": "array of strings | empty",
            },
        }
