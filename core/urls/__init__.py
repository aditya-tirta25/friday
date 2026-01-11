from django.urls import path, include

from core.views import LoginView, LogoutView, DashboardView, TodoListView

urlpatterns = [
    # Auth
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),

    # Dashboard
    path("", DashboardView.as_view(), name="dashboard"),

    # Todos
    path("todos/", TodoListView.as_view(), name="todo_list"),
]
