"""
URL configuration for friday project.
"""
from django.contrib import admin
from django.urls import path
from ninja import NinjaAPI

from core.apis import auth_router, room_router, whatsapp_router

api = NinjaAPI(title="Friday Matrix Monitor API", version="1.0.0")

api.add_router("/_matrix/client/v3", auth_router, tags=["Matrix Auth"])
api.add_router("/rooms", room_router, tags=["Rooms"])
api.add_router("/whatsapp", whatsapp_router, tags=["WhatsApp"])

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', api.urls),
]
