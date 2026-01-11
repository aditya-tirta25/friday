from typing import Optional
from ninja import Router, Schema
from ninja.errors import HttpError
from django.shortcuts import get_object_or_404

from core.models import TodoList, SubscriberRoom

router = Router()


class TodoCreate(Schema):
    description: str
    room_id: Optional[int] = None
    notes: Optional[str] = ""


class TodoStatusUpdate(Schema):
    status: str


class TodoResponse(Schema):
    id: int
    description: str
    status: str
    status_display: str
    notes: str
    room_id: Optional[int] = None
    room_name: Optional[str] = None


class SuccessResponse(Schema):
    success: bool
    message: Optional[str] = None


def _todo_response(todo: TodoList) -> TodoResponse:
    """Helper to build TodoResponse."""
    return TodoResponse(
        id=todo.id,
        description=todo.description,
        status=todo.status,
        status_display=todo.get_status_display(),
        notes=todo.notes,
        room_id=todo.room_id,
        room_name=todo.room.room_name if todo.room else None,
    )


@router.post("", response=TodoResponse)
def create_todo(request, payload: TodoCreate):
    """Create a new todo item."""
    room = None
    if payload.room_id:
        room = get_object_or_404(SubscriberRoom, id=payload.room_id)

    todo = TodoList.objects.create(
        description=payload.description,
        room=room,
        notes=payload.notes or "",
    )

    return _todo_response(todo)


@router.patch("/{todo_id}/status", response=TodoResponse)
def update_todo_status(request, todo_id: int, payload: TodoStatusUpdate):
    """Update todo status."""
    todo = get_object_or_404(TodoList, id=todo_id)

    valid_statuses = [TodoList.STATUS_PENDING, TodoList.STATUS_DONE, TodoList.STATUS_CANCELLED]
    if payload.status not in valid_statuses:
        raise HttpError(400, f"Invalid status. Must be one of: {', '.join(valid_statuses)}")

    todo.status = payload.status
    todo.save(update_fields=["status", "updated_at"])

    return _todo_response(todo)


@router.delete("/{todo_id}", response=SuccessResponse)
def delete_todo(request, todo_id: int):
    """Delete a todo item."""
    todo = get_object_or_404(TodoList, id=todo_id)
    todo.delete()

    return SuccessResponse(success=True, message="Todo deleted successfully")


@router.get("/{todo_id}", response=TodoResponse)
def get_todo(request, todo_id: int):
    """Get a single todo item."""
    todo = get_object_or_404(TodoList, id=todo_id)

    return _todo_response(todo)
