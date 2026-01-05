from ninja import Router

from core.schemas.llm import LLMContextRequest, LLMContextResponse
from core.services.llm import LLMService

router = Router()


@router.post("/context", response=LLMContextResponse)
def construct_llm_context(request, payload: LLMContextRequest):
    """
    Construct LLM context from a list of messages.

    Takes messages and formats them for LLM processing with
    sender mapping, goals, and response rules.

    Body:
        messages: List of message objects with sender and content
    """
    llm_service = LLMService()

    messages = [{"sender": m.sender, "content": m.content} for m in payload.messages]
    context = llm_service.build_context(messages)

    return context
