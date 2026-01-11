"""
URL configuration for friday project.
"""
from django.contrib import admin
from django.urls import path, include
from ninja import NinjaAPI

from core.apis import auth_router, matrix_router, whatsapp_router, llm_router, todo_router

api = NinjaAPI(title="Friday Matrix Monitor API", version="1.0.0")

api.add_router("/_matrix/client/v3", auth_router, tags=["Matrix Auth"])
api.add_router("/matrix", matrix_router, tags=["Matrix"])
api.add_router("/whatsapp", whatsapp_router, tags=["WhatsApp"])
api.add_router("/llm", llm_router, tags=["LLM"])
api.add_router("/todos", todo_router, tags=["Todos"])

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", api.urls),
    path("", include("core.urls")),
]
