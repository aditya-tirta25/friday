from django.db import models
from django.db.models import Q


class Subscription(models.Model):
    STATUS_CHOICES = [
        ("active", "Active"),
        ("past_due", "Past Due"),
        ("canceled", "Canceled"),
        ("expired", "Expired"),
    ]

    subscriber = models.ForeignKey("Subscriber", on_delete=models.CASCADE)
    plan = models.ForeignKey("Plan", on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    start_at = models.DateField()
    end_at = models.DateField()
    auto_renew = models.BooleanField(default=True)
    canceled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["subscriber", "status"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["subscriber"],
                condition=Q(status="active"),
                name="one_active_subscription_per_user",
            )
        ]
