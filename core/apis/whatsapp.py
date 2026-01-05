from ninja import Router
from ninja.errors import HttpError

from core.auth import BearerAuth
from core.services.whatsapp import WhatsAppService

router = Router(auth=BearerAuth())


@router.get("/rooms")
def list_rooms(request):
    """
    List all WhatsApp-bridged rooms with optional filtering.

    Requires Authorization header with Bearer token.
    Query parameters are used as filter criteria (e.g., ?creator=@user:matrix.org).
    Each query param key should match a room field name.
    """
    whatsapp_service = WhatsAppService(access_token=request.auth)

    try:
        filters = dict(request.GET.items())
        rooms = whatsapp_service.list_rooms(**filters)
        return {"rooms": rooms, "total": len(rooms)}
    except Exception as e:
        raise HttpError(500, f"Failed to list rooms: {str(e)}")
