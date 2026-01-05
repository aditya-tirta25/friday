from typing import List, Dict, Any
from django.conf import settings


class LLMService:
    """Service for LLM-related operations."""

    def __init__(self):
        self.actor_id = settings.MATRIX_CONFIG['USERNAME']

    def build_context(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Build LLM context from a list of messages.

        Args:
            messages: List of dicts with 'sender' and 'content' keys

        Returns:
            Complete LLM context dictionary
        """
        sender_mapping = {self.actor_id: "yourself"}
        for msg in messages:
            sender = msg.get("sender", "")
            if sender and sender not in sender_mapping:
                sender_mapping[sender] = sender

        return {
            "messages": [
                {"sender": m["sender"], "content": m["content"]}
                for m in messages
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
                "summary": "string",
                "reply": "string | null",
                "needs_more_information": "boolean",
                "todo_list": "array of strings | empty",
            },
        }
