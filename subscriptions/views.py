import json
import stripe
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from accounts.models import CustomUser
from subscriptions.models import Subscription
from stripe import SignatureVerificationError

stripe.api_key = settings.STRIPE_SECRET_KEY


@csrf_exempt
def create_checkout_session(request):
    if request.method != "GET":
        return JsonResponse({"error": "Método no permitido"}, status=405)

    plan = request.GET.get("plan")
    user = request.user

    if not user.is_authenticated:
        return JsonResponse({"error": "Debes iniciar sesión"}, status=401)

    PLAN_PRICE_MAP = {
        "basic": settings.STRIPE_PRICE_BASIC,
        "profesor": settings.STRIPE_PRICE_PROFESOR,
        "superpro": settings.STRIPE_PRICE_SUPERPRO,
        "superprofesor": settings.STRIPE_PRICE_SUPERPROFESOR,
    }

    price_id = PLAN_PRICE_MAP.get(plan)

    if not price_id:
        return JsonResponse({"error": "Plan inválido"}, status=400)

    # Crear la sesión de Stripe Checkout
    session = stripe.checkout.Session.create(
    mode="subscription",
    payment_method_types=["card"],
    customer_email=user.email,
    client_reference_id=str(user.id),
    line_items=[{ "price": price_id, "quantity": 1 }],
    success_url="https://tu-app.com/success",
    cancel_url="https://tu-app.com/cancel",)


    return JsonResponse({"url": session.url})

@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    webhook_secret = settings.STRIPE_WEBHOOK_SECRET

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except Exception:
        return HttpResponse(status=400)

    event_type = event["type"]
    data = event["data"]["object"]

    # ==========================================================
    # 1️⃣ CHECKOUT SESSION COMPLETED → CREAR SUSCRIPCIÓN PENDIENTE
    # ==========================================================
    if event_type == "checkout.session.completed":
        user_id = data.get("client_reference_id")
        stripe_customer_id = data.get("customer")
        plan_type = data.get("metadata", {}).get("plan_type", "basic")

        if user_id and stripe_customer_id:
            Subscription.objects.update_or_create(
                user_id=user_id,
                defaults={
                    "stripe_customer_id": stripe_customer_id,
                    "plan_type": plan_type,     # 💥 ya no es NULL
                    "status": "pending",
                }
            )

        return HttpResponse(status=200)

    # ==========================================================
    # 2️⃣ SUBSCRIPTION CREATED / UPDATED (ESTE ES EL IMPORTANTE 🔥)
    # ==========================================================
    if event_type in ["customer.subscription.created", "customer.subscription.updated"]:

        stripe_subscription_id = data["id"]
        stripe_customer_id = data["customer"]

        stripe_sub = stripe.Subscription.retrieve(stripe_subscription_id)

        # periodo
        current_period_end_ts = stripe_sub.get("current_period_end")
        current_period_end = (
            timezone.datetime.fromtimestamp(current_period_end_ts, tz=timezone.utc)
            if current_period_end_ts else None
        )

        # extraer plan correcto
        price_id = stripe_sub["items"]["data"][0]["price"]["id"]

        PRICE_PLAN_REVERSE_MAP = {
            settings.STRIPE_PRICE_BASIC: "basic",
            settings.STRIPE_PRICE_PROFESOR: "profesor",
            settings.STRIPE_PRICE_SUPERPRO: "superpro",
            settings.STRIPE_PRICE_SUPERPROFESOR: "superprofesor",
        }

        plan_type = PRICE_PLAN_REVERSE_MAP.get(price_id, "basic")

        # actualizar o crear
        subscription, created = Subscription.objects.update_or_create(
            stripe_customer_id=stripe_customer_id,
            defaults={
                "stripe_subscription_id": stripe_subscription_id,
                "status": stripe_sub["status"],
                "current_period_end": current_period_end,
                "plan_type": plan_type,
            }
        )

        # activar VIP
        if subscription.status == "active":
            user = subscription.user
            user.is_vip = True
            user.save()

        return HttpResponse(status=200)

    # ==========================================================
    # 3️⃣ RENOVACIÓN DE PAGO
    # ==========================================================
    if event_type in ["invoice.payment_succeeded", "invoice.paid"]:

        stripe_customer_id = data.get("customer")

        subscription = Subscription.objects.filter(
            stripe_customer_id=stripe_customer_id
        ).first()

        if subscription:
            user = subscription.user
            user.is_vip = True
            user.save()

            paid_sub_id = data.get("subscription")
            if paid_sub_id:
                stripe_sub = stripe.Subscription.retrieve(paid_sub_id)

                new_end_ts = stripe_sub.get("current_period_end")
                if new_end_ts:
                    subscription.current_period_end = timezone.datetime.fromtimestamp(
                        new_end_ts, tz=timezone.utc
                    )
                    subscription.status = stripe_sub["status"]
                    subscription.save()

        return HttpResponse(status=200)

    return HttpResponse(status=200)



@csrf_exempt
def member_area(request):
    if request.method != "POST":
        return JsonResponse({"error": "Método no permitido"}, status=405)

    data = json.loads(request.body)
    user_id = data.get("user_id")

    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        return JsonResponse({"error": "Usuario no encontrado"}, status=404)

    # No es VIP
    if not user.is_vip:
        return JsonResponse({"error": "No tienes suscripción activa"}, status=403)

    # Fecha expirada
    if user.subscription_expires_at and user.subscription_expires_at < timezone.now():
        user.is_vip = False
        user.subscription_expires_at = None
        user.save()
        return JsonResponse({"error": "Tu suscripción expiró"}, status=403)

    return JsonResponse({"message": "Bienvenido a la zona VIP 🚀"})