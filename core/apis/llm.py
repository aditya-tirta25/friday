from ninja import Router
from ninja.errors import HttpError

from core.schemas.llm import LLMContextRequest, LLMContextResponse, LLMProcessResponse
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

    messages = [{"sender": m.sender, "content": m.body} for m in payload.messages]
    context = llm_service.build_context(messages)

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
