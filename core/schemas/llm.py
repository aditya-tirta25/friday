from typing import List, Optional
from ninja import Schema


class MessageItemRequest(Schema):
    """Single message item for LLM context."""

    sender: str
    body: str


class MessageItem(Schema):
    """Single message item for LLM context."""

    sender: str
    content: str


class LLMContextRequest(Schema):
    """Request schema for constructing LLM context."""

    messages: List[MessageItemRequest]


class LLMContextResponse(Schema):
    """Response schema for LLM context."""

    messages: List[MessageItem]
    sender_mapping: dict
    goals: dict
    response_rules: dict
    output_format: dict


class LLMProcessResponse(Schema):
    """Response schema for LLM processing output."""

    summary: str
    reply: Optional[str] = None
    needs_more_information: bool
    todo_list: List[str] = []
