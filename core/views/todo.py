from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin

from core.models import TodoList, SubscriberRoom


class TodoListView(LoginRequiredMixin, ListView):
    """Display todo list with filters."""

    model = TodoList
    template_name = "todo/list.html"
    context_object_name = "todos"
    paginate_by = 20
    login_url = "login"

    def get_queryset(self):
        queryset = TodoList.objects.select_related(
            "room", "room__subscriber"
        ).order_by("-created_at")

        # Apply filters
        status_filter = self.request.GET.get("status", "")
        room_filter = self.request.GET.get("room", "")
        search_query = self.request.GET.get("q", "")

        if status_filter:
            queryset = queryset.filter(status=status_filter)

        if room_filter:
            queryset = queryset.filter(room_id=room_filter)

        if search_query:
            queryset = queryset.filter(description__icontains=search_query)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get rooms for filter dropdown
        context["rooms"] = SubscriberRoom.objects.filter(
            is_active=True
        ).select_related("subscriber")

        # Get stats
        context["stats"] = {
            "total": TodoList.objects.count(),
            "pending": TodoList.objects.filter(status=TodoList.STATUS_PENDING).count(),
            "done": TodoList.objects.filter(status=TodoList.STATUS_DONE).count(),
            "cancelled": TodoList.objects.filter(status=TodoList.STATUS_CANCELLED).count(),
        }

        # Preserve filter values
        context["status_filter"] = self.request.GET.get("status", "")
        context["room_filter"] = self.request.GET.get("room", "")
        context["search_query"] = self.request.GET.get("q", "")
        context["status_choices"] = TodoList.STATUS_CHOICES

        return context
