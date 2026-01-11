from django.db import models
from django.utils import timezone


class RoomDailySummaryCount(models.Model):
    """Track daily summary count per SubscriberRoom."""

    room = models.ForeignKey(
        "SubscriberRoom",
        on_delete=models.CASCADE,
        related_name="daily_summary_counts",
    )
    date = models.DateField(default=timezone.now, db_index=True)
    count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["room", "date"]
        ordering = ["-date"]

    def __str__(self):
        return f"{self.room} - {self.date}: {self.count}"


class ConversationProcessingState(models.Model):
    STATUS_IDLE = "idle"
    STATUS_READY = "ready"
    STATUS_PROCESSING = "processing"
    STATUS_FAILED = "failed"

    STATUS_CHOICES = [
        (STATUS_IDLE, "Idle"),
        (STATUS_READY, "Ready"),
        (STATUS_PROCESSING, "Processing"),
        (STATUS_FAILED, "Failed"),
    ]
    room = models.ForeignKey("SubscriberRoom", on_delete=models.CASCADE)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_IDLE,
        db_index=True,
    )
    llm_context_to_process = models.JSONField(null=True, blank=True)
    last_message_synced_at = models.DateTimeField(null=True, blank=True)
    last_summarized_at = models.DateTimeField(null=True, blank=True)
    processing_started_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)


class RoomSummary(models.Model):
    """Store generated summaries for subscriber rooms."""

    room = models.ForeignKey(
        "SubscriberRoom",
        on_delete=models.CASCADE,
        related_name="summaries",
    )
    summary = models.TextField()
    reply = models.TextField(blank=True, null=True)
    needs_more_information = models.BooleanField(default=False)
    todo_list = models.JSONField(default=list, blank=True)
    message_count = models.PositiveIntegerField(default=0)
    from_timestamp = models.DateTimeField(null=True, blank=True)
    to_timestamp = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True, db_index=True)
    send_failed_at = models.DateTimeField(null=True, blank=True)
    send_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "Room summaries"

    def __str__(self):
        return f"{self.room} - {self.created_at}"
