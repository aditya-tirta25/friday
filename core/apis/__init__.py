from core.apis.auth_api import router as auth_router
from core.apis.room_api import router as room_router
from core.apis.whatsapp import router as whatsapp_router

__all__ = ['auth_router', 'room_router', 'whatsapp_router']
