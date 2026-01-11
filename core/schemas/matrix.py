from ninja import Schema
from typing import Optional, List
from datetime import datetime


class RoomSchema(Schema):
    """Schema for room data."""

    id: int
    room_id: str
    name: Optional[str] = None
    creator: str
    member_count: int
    room_created_at: Optional[datetime] = None
    is_checked: bool
    last_checked_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class RoomListResponse(Schema):
    """Response for listing rooms."""

    rooms: List[RoomSchema]
    total_count: int


class RoomSyncResponse(Schema):
    """Response for room sync operation."""

    synced_count: int
    new_rooms: int
    updated_rooms: int
    message: str


class TodoItem(Schema):
    """A single todo item for room review."""

    room_id: str
    room_name: Optional[str] = None
    action: str
    priority: str


class ActionItem(Schema):
    """An action item extracted from conversation."""

    description: str
    assignee: Optional[str] = None
    due_date: Optional[str] = None
    priority: str  # high|medium|low


class RoomSummaryResponse(Schema):
    """Response for unchecked rooms with AI summary."""

    rooms: List[RoomSchema]
    total_unchecked: int
    summary: str
    todo_list: List[TodoItem]


class RoomCheckResponse(Schema):
    """Response for marking a room as checked."""

    room: RoomSchema
    message: str


class ConversationSummaryResponse(Schema):
    """Response for room conversation summary."""

    room: RoomSchema
    summary: str
    action_items: List[ActionItem]
    message_count: int
    from_timestamp: Optional[datetime] = None
    to_timestamp: datetime
    check_log_id: int


class RoomMessagesRequest(Schema):
    """Request schema for fetching room messages."""

    subscriber_id: int
    room_id: str
    room_name: str
    platform: str = "whatsapp"
    limit: int = 100
