from django.db import models


class Plan(models.Model):
    BILLING_PERIOD_CHOICES = [
        ("monthly", "Monthly"),
        ("yearly", "Yearly"),
    ]
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default="IDR")
    billing_period = models.CharField(max_length=10, choices=BILLING_PERIOD_CHOICES)
    # Feature limits
    number_of_rooms = models.PositiveIntegerField(default=3)
    daily_summary_quota_per_room = models.PositiveIntegerField(default=3)
    version = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.billing_period})"
