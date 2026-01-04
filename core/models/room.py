from django.db import models


class Room(models.Model):
    """Matrix room model to track rooms created by the target user."""

    room_id = models.CharField(max_length=255, unique=True, db_index=True)
    name = models.CharField(max_length=500, blank=True, null=True)
    creator = models.CharField(max_length=255, db_index=True)
    member_count = models.IntegerField(default=0)
    room_created_at = models.DateTimeField(null=True, blank=True)
    is_checked = models.BooleanField(default=False, db_index=True)
    last_checked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Room'
        verbose_name_plural = 'Rooms'

    def __str__(self):
        return f"{self.name or self.room_id} ({self.creator})"


class RoomCheckLog(models.Model):
    """Line item to track room check history with summaries."""

    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        related_name='check_logs'
    )
    checked_at = models.DateTimeField(auto_now_add=True)
    summary = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-checked_at']
        verbose_name = 'Room Check Log'
        verbose_name_plural = 'Room Check Logs'

    def __str__(self):
        return f"Check for {self.room.room_id} at {self.checked_at}"
