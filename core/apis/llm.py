from ninja import Router
from ninja.errors import HttpError

from core.auth import BearerAuth
from core.schemas.llm import (
    LLMContextRequest,
    LLMContextResponse,
    LLMProcessResponse,
    SendSummaryRequest,
)
from core.services.llm import LLMService
from core.services.matrix import MatrixService

router = Router()
bearer_auth = BearerAuth()


@router.post("/context", response=LLMContextResponse, auth=bearer_auth)
def construct_llm_context(request, payload: LLMContextRequest):
    """
    Construct LLM context from a list of messages.

    Takes messages and formats them for LLM processing with
    sender mapping, goals, and response rules.

    Body:
        room: Room object with id, name, and platform
        messages: List of message objects with sender and content
        yourself: The user_id that represents "yourself"
    """
    llm_service = LLMService()
    access_token = request.auth

    room = {
        "id": payload.room.id,
        "name": payload.room.name,
        "platform": payload.room.platform,
    }
    messages = [{"sender": m.sender, "content": m.body} for m in payload.messages]
    context = llm_service.build_context(
        room=room,
        messages=messages,
        yourself=payload.yourself,
        access_token=access_token,
    )

    return context


@router.post("/summarize", response=LLMProcessResponse)
def summarize_context(request, payload: LLMContextResponse, model: str = "gpt-5.1"):
    """
    Process LLM context and get summary, reply, and action items.

    Sends the context to NanoGPT and returns structured output.

    Body:
        messages: List of message objects
        sender_mapping: Mapping of senders
        goals: Processing goals
        response_rules: Rules for response generation
        output_format: Expected output format

    Query params:
        model: LLM model to use (default: gpt-4o-mini)
    """
    llm_service = LLMService()

    try:
        context = {
            "room": {
                "id": payload.room.id,
                "name": payload.room.name,
                "platform": payload.room.platform,
            },
            "messages": [
                {"sender": m.sender, "content": m.content} for m in payload.messages
            ],
            "sender_mapping": payload.sender_mapping,
            "goals": payload.goals,
            "response_rules": payload.response_rules,
            "output_format": payload.output_format,
        }

        result = llm_service.process(context=context, model=model)
        return result
    except Exception as e:
        raise HttpError(500, f"LLM processing failed: {str(e)}")


@router.post("/send", auth=bearer_auth)
def send_summary(request, payload: SendSummaryRequest):
    """
    Send LLM summary response to a Matrix room.

    Body:
        room_id: Matrix room ID to send the message to
        summary: LLMProcessResponse object with summary, reply, todo_list
    """
    access_token = request.auth
    matrix_service = MatrixService()

    summary = payload.summary
    lines = [
        f"📋 Room: {summary.room.name} ({summary.room.platform})",
        f"📝 Summary: {summary.summary}",
    ]

    if summary.reply:
        lines.append(f"💬 Reply: {summary.reply}")

    if summary.needs_more_information:
        lines.append("⚠️ Needs more information")

    if summary.todo_list:
        lines.append("📌 Todo:")
        for item in summary.todo_list:
            lines.append(f"  • {item}")

    message = "\n".join(lines)

    try:
        result = matrix_service.send_message(
            room_id=payload.room_id,
            body=message,
            access_token=access_token,
        )
        return {"success": True, "event_id": result.get("event_id")}
    except Exception as e:
        raise HttpError(500, f"Failed to send message: {str(e)}")
