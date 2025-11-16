import json
import stripe
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from accounts.models import CustomUser
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
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError:
        return HttpResponse(status=400)
    except SignatureVerificationError:
        return HttpResponse(status=400)

    # === Pago exitoso ===
    if event["type"] == "checkout.session.completed":
       session = event["data"]["object"]
   
       user_id = session.get("client_reference_id")
   
       if user_id:
           try:
               user = CustomUser.objects.get(id=user_id)
               user.is_vip = True
               user.subscription_expires_at = timezone.now() + timedelta(days=30)
               user.save()
           except CustomUser.DoesNotExist:
               pass
   
    # === Pago fallido ===
    elif event["type"] == "invoice.payment_failed":
        invoice = event["data"]["object"]
        email = invoice.get("customer_email")

        if email:
            try:
                user = CustomUser.objects.get(email=email)
                user.is_vip = False
                user.subscription_expires_at = None
                user.save()
            except CustomUser.DoesNotExist:
                pass

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
