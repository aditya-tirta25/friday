from django.db import models


class ObservedRoom(models.Model):
    """Rooms being watched across various platforms."""

    PLATFORM_CHOICES = [
        ('whatsapp', 'WhatsApp'),
        ('teams', 'Teams'),
        ('matrix', 'Matrix'),
    ]

    platform = models.CharField(
        max_length=20,
        choices=PLATFORM_CHOICES,
        db_index=True,
    )
    platform_room_id = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text="Room/channel ID for the platform",
    )
    name = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Display name of the room/channel",
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.platform}] {self.name or self.platform_room_id}"
