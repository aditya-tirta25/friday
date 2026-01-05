from typing import List
from ninja import Schema


class MessageItem(Schema):
    """Single message item for LLM context."""

    sender: str
    content: str


class LLMContextRequest(Schema):
    """Request schema for constructing LLM context."""

    messages: List[MessageItem]


class LLMContextResponse(Schema):
    """Response schema for LLM context."""

    messages: List[MessageItem]
    sender_mapping: dict
    goals: dict
    response_rules: dict
    output_format: dict
