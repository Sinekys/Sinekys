# subscriptions/models.py

from django.db import models
from django.utils import timezone
from accounts.models import CustomUser
from django.conf import settings

class Subscription(models.Model):
    PLAN_CHOICES = [
        ("basic", "Basic"),
        ("profesor", "Profesor"),
        ("superpro", "Super Pro"),
        ("superprofesor", "Super Profesor"),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)

    plan_type = models.CharField(
        max_length=30,
        choices=PLAN_CHOICES,
        default="basic"   # ⬅️ IMPORTANTE
    )

    stripe_customer_id = models.CharField(max_length=255, null=True, blank=True)
    stripe_subscription_id = models.CharField(max_length=255, null=True, blank=True)

    status = models.CharField(max_length=50, default="inactive")
    current_period_end = models.DateTimeField(null=True, blank=True)

    def is_active(self):
        return self.current_period_end and self.current_period_end > timezone.now()

    def activate_from_stripe(self, stripe_subscription):
        self.stripe_subscription_id = stripe_subscription["id"]
        self.status = stripe_subscription["status"]
        self.current_period_end = timezone.datetime.fromtimestamp(
            stripe_subscription["current_period_end"], tz=timezone.utc
        )

        # Detectar plan
        price_id = stripe_subscription["items"]["data"][0]["price"]["id"]

        PRICE_PLAN_REVERSE_MAP = {
            settings.STRIPE_PRICE_BASIC: "basic",
            settings.STRIPE_PRICE_PROFESOR: "profesor",
            settings.STRIPE_PRICE_SUPERPRO: "superpro",
            settings.STRIPE_PRICE_SUPERPROFESOR: "superprofesor",
        }

        if price_id in PRICE_PLAN_REVERSE_MAP:
            self.plan_type = PRICE_PLAN_REVERSE_MAP[price_id]

        self.save()

    def __str__(self):
        return f"{self.user.email} - {self.plan_type} ({self.status})"
