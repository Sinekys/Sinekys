from datetime import date
from usage.models import DailyQuota
from subscriptions.models import Subscription


# Límites por plan
PLAN_LIMITS = {
    "basic": 15,
    "superpro": 50,
    "profesor": None,        # ilimitado
    "superprofesor": None,   # ilimitado
}


def can_user_attempt(user):
    today = date.today()

    # Obtener o crear DailyQuota para hoy
    quota, _ = DailyQuota.objects.get_or_create(
        user=user,
        date=today,
        defaults={"attempts_count": 0, "messages_count": 0}
    )

    # Obtener suscripción activa
    subscription = Subscription.objects.filter(
        user=user,
        status="active"
    ).first()

    # Si NO tiene suscripción => límite FREE = 3 intentos por día
    if subscription is None:
        limit = 50
    else:
        limit = PLAN_LIMITS.get(subscription.plan_type, 3)

    # Si tiene límite y ya lo alcanzó → bloquear
    if limit is not None and quota.attempts_count >= limit:
        return False, limit, quota.attempts_count

    # Sino → puede intentar
    return True, limit, quota.attempts_count


def register_attempt(user):
    today = date.today()

    quota, _ = DailyQuota.objects.get_or_create(
        user=user,
        date=today,
        defaults={"attempts_count": 0, "messages_count": 0}
    )

    quota.attempts_count += 1
    quota.save()

    return quota.attempts_count
