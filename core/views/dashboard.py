from django.db import models
from django.db.models import Count, Q
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

from core.models import TodoList, Subscriber, SubscriberRoom, RoomSummary


class DashboardView(LoginRequiredMixin, TemplateView):
    """Dashboard with overview stats."""

    template_name = "dashboard/index.html"
    login_url = "login"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get todo stats
        context["todo_stats"] = TodoList.objects.aggregate(
            total=Count("id"),
            pending=Count("id", filter=Q(status=TodoList.STATUS_PENDING)),
            done=Count("id", filter=Q(status=TodoList.STATUS_DONE)),
            cancelled=Count("id", filter=Q(status=TodoList.STATUS_CANCELLED)),
        )

        # Get recent todos
        context["recent_todos"] = TodoList.objects.select_related(
            "room", "room__subscriber"
        ).order_by("-created_at")[:5]

        # Get subscriber stats
        context["subscriber_count"] = Subscriber.objects.filter(is_active=True).count()
        context["room_count"] = SubscriberRoom.objects.filter(is_active=True).count()

        # Get recent summaries
        context["recent_summaries"] = RoomSummary.objects.select_related(
            "room", "room__subscriber"
        ).order_by("-created_at")[:5]

        return context
