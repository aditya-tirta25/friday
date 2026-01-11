import secrets

from django.db import models


# Alphanumeric without confusing characters (0/O, 1/l/I)
ROOM_CODE_ALPHABET = "23456789abcdefghjkmnpqrstuvwxyz"
ROOM_CODE_LENGTH = 4


class Subscriber(models.Model):
    """Users who subscribe to the room observation service."""

    full_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )
    email = models.EmailField(
        blank=True,
        null=True,
    )
    phone_number = models.CharField(blank=True, null=True)
    matrix_room_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Matrix room ID for sending notifications (subscriber's WhatsApp)",
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Whether subscription is active (payment valid)",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.full_name}"

    @property
    def matrix_id(self):
        """
        Generate Matrix user ID from phone number for WhatsApp bridge.
        Returns format: @whatsapp_{phone_number}:matrix.tirta.me
        """
        if not self.phone_number:
            return None
        return f"@whatsapp_{self.phone_number}:matrix.tirta.me"


class SubscriberRoom(models.Model):
    """Rooms that a subscriber wants us to observe."""

    PLATFORM_CHOICES = [
        ("whatsapp", "WhatsApp"),
        ("teams", "Teams"),
        ("matrix", "Matrix"),
    ]

    subscriber = models.ForeignKey(
        Subscriber,
        on_delete=models.CASCADE,
        related_name="rooms",
    )
    platform = models.CharField(
        max_length=20,
        choices=PLATFORM_CHOICES,
        db_index=True,
    )
    room_id = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Matrix room ID",
    )
    room_code = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Short code for the room (e.g., 'family', 'work')",
    )
    room_name = models.CharField(
        max_length=500,
        blank=True,
        null=True,
    )
    last_read_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Timestamp of last scanned message",
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ["subscriber", "room_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["subscriber", "room_code"],
                name="unique_subscriber_room_code",
                condition=models.Q(room_code__isnull=False),
            ),
        ]

    def __str__(self):
        return f"{self.subscriber} - {self.room_name or self.room_id}"

    def save(self, *args, **kwargs):
        if not self.room_code:
            self.room_code = self._generate_unique_code()
        super().save(*args, **kwargs)

    def _generate_unique_code(self):
        """Generate a unique room code for this subscriber."""
        for _ in range(10):  # Max 10 attempts
            code = "".join(
                secrets.choice(ROOM_CODE_ALPHABET) for _ in range(ROOM_CODE_LENGTH)
            )
            # Check uniqueness within this subscriber's rooms
            if not SubscriberRoom.objects.filter(
                subscriber=self.subscriber, room_code=code
            ).exists():
                return code
        # Fallback: append random char if all attempts fail
        return code + secrets.choice(ROOM_CODE_ALPHABET)
