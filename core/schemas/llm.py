from typing import List, Optional, Literal
from ninja import Schema


class RoomInfo(Schema):
    """Room information for LLM context."""

    id: str
    name: str
    platform: Literal["whatsapp", "teams"]


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

    room: RoomInfo
    messages: List[MessageItemRequest]
    yourself: str


class LLMContextResponse(Schema):
    """Response schema for LLM context."""

    room: RoomInfo
    messages: List[MessageItem]
    sender_mapping: dict
    goals: dict
    response_rules: dict
    output_format: dict


class LLMProcessResponse(Schema):
    """Response schema for LLM processing output."""

    room: RoomInfo
    summary: str
    reply: Optional[str] = None
    needs_more_information: bool
    todo_list: List[str] = []


class SendSummaryRequest(Schema):
    """Request schema for sending summary to Matrix."""

    room_id: str
    summary: LLMProcessResponse
