import json
import requests
from typing import List, Dict, Any
from django.conf import settings


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
            Dict with summary, reply, needs_more_information, todo_list
        """
        prompt = f"""You are an assistant analyzing a conversation. Here is the context:

{json.dumps(context, indent=2)}

Based on the context above, provide a response following the output_format specified in the context"""

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
                return result
        except (json.JSONDecodeError, ValueError):
            pass

        return {
            "summary": content,
            "reply": None,
            "needs_more_information": False,
            "todo_list": [],
        }

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
                "summary": "string",
                "reply": "string | null",
                "needs_more_information": "boolean",
                "todo_list": "array of strings | empty",
            },
        }
