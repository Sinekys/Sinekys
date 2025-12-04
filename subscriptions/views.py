import json
import stripe
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import datetime, timezone as dt_timezone
from django.conf import settings
from accounts.models import CustomUser
from subscriptions.models import Subscription
from stripe import SignatureVerificationError

# Configurar clave secreta de Stripe solo si está disponible
if settings.STRIPE_SECRET_KEY:
    stripe.api_key = settings.STRIPE_SECRET_KEY


@csrf_exempt
def create_checkout_session(request):
    """
    Crea una sesión de Stripe Checkout para iniciar una suscripción.
    """
    if request.method != "GET":
        return JsonResponse({"error": "Método no permitido"}, status=405)

    plan = request.GET.get("plan")
    user = request.user

    if not user.is_authenticated:
        return JsonResponse({"error": "Debes iniciar sesión"}, status=401)

    # Asegúrate de que estos mapeos coincidan con tus settings
    PLAN_PRICE_MAP = {
        "basic": settings.STRIPE_PRICE_BASIC,
        "profesor": settings.STRIPE_PRICE_PROFESOR,
        "superpro": settings.STRIPE_PRICE_SUPERPRO,
        "superprofesor": settings.STRIPE_PRICE_SUPERPROFESOR,
    }

    price_id = PLAN_PRICE_MAP.get(plan)

    if not price_id:
        return JsonResponse({"error": "Plan inválido"}, status=400)

    try:
        # Crear la sesión de Stripe Checkout
        session = stripe.checkout.Session.create(
            mode="subscription",
            payment_method_types=["card"],
            customer_email=user.email,
            client_reference_id=str(user.id),
            line_items=[{ "price": price_id, "quantity": 1 }],
            success_url="http://127.0.0.1:8000/",
            cancel_url="https://tu-app.com/cancel",
        )
    except Exception as e:
        # Manejo básico de errores de Stripe
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"url": session.url})



@csrf_exempt
def stripe_webhook(request):
    """
    Maneja los eventos de webhook de Stripe para sincronizar el estado
    de la suscripción en la base de datos de Django.
    """
    # Si no hay webhook secret, rechazar silenciosamente (desarrollo sin Stripe)
    if not settings.STRIPE_WEBHOOK_SECRET:
        return HttpResponse(status=200)
    
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    webhook_secret = settings.STRIPE_WEBHOOK_SECRET

    try:
        # Construir el evento de Stripe para verificación de firma
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except SignatureVerificationError as e:
        print(f"⚠️ Error de verificación de firma: {e}")
        return HttpResponse(status=400)
    except Exception as e:
        print(f"⚠️ Error general al procesar el webhook: {e}")
        return HttpResponse(status=400)


    event_type = event["type"]
    data = event["data"]["object"]
    print(f"✨ Webhook Recibido: {event_type}")

    # ==========================================================
    # 1️⃣ CHECKOUT COMPLETED — crear relación inicial
    # Se asegura de que la relación user_id <-> stripe_customer_id exista.
    # ==========================================================
    if event_type == "checkout.session.completed":

        user_id = data.get("client_reference_id")
        stripe_customer_id = data.get("customer")
        stripe_subscription_id = data.get("subscription") 
        
        # En este punto, solo necesitamos asegurar la existencia de la Subscription
        # para que el evento customer.subscription.created/updated pueda actualizarla.
        if user_id and stripe_customer_id:
            try:
                Subscription.objects.update_or_create(
                    user_id=user_id,
                    defaults={
                        "stripe_customer_id": stripe_customer_id,
                        "stripe_subscription_id": stripe_subscription_id, 
                        "status": "pending", 
                    }
                )
            except Exception as e:
                print(f"Error al crear/actualizar suscripción en checkout: {e}")
                return HttpResponse(status=500)
                
        return HttpResponse(status=200)

    # ==========================================================
    # 2️⃣ SUBSCRIPTION CREATED / UPDATED — evento clave (Creación y Renovación)
    # Este evento obtiene la fecha current_period_end y la guarda en ambos modelos.
    # ==========================================================
    if event_type in ["customer.subscription.created", "customer.subscription.updated"]:

        stripe_subscription_id = data["id"]
        stripe_customer_id = data["customer"]

        # Recuperar la suscripción de Stripe para obtener la info más reciente
        stripe_sub = stripe.Subscription.retrieve(stripe_subscription_id)

        # Extraer el 'current_period_end' (Timestamp Unix)
        ts = stripe_sub.get("current_period_end")
        
        # Convertir el timestamp Unix a objeto datetime con zona horaria UTC
        current_period_end = (
            datetime.fromtimestamp(ts, tz=dt_timezone.utc)
            if ts else None
        )

        # Mapear el ID de precio de Stripe a tu tipo de plan local
        price_id = stripe_sub["items"]["data"][0]["price"]["id"]
        PRICE_MAP = {
            settings.STRIPE_PRICE_BASIC: "basic",
            settings.STRIPE_PRICE_PROFESOR: "profesor",
            settings.STRIPE_PRICE_SUPERPRO: "superpro",
            settings.STRIPE_PRICE_SUPERPROFESOR: "superprofesor",
        }
        plan_type = PRICE_MAP.get(price_id, "basic")
        
        try:
            # 1. Guardar/Actualizar en Subscription (usando stripe_customer_id como clave)
            # Esto funcionará para CREACIÓN (si checkout.session.completed creó la Subscription antes)
            # y para ACTUALIZACIÓN/RENOVACIÓN.
            subscription = Subscription.objects.filter(
                stripe_customer_id=stripe_customer_id
            ).first()

            if not subscription:
                # Si la Subscription no se creó en el paso 1 (orden de eventos atípico),
                # intenta crearla usando el customer ID y asume el user_id de la cuenta relacionada.
                # (REQUIERE QUE TENGAS UNA RELACIÓN ENTRE STRIPE_CUSTOMER_ID Y USER EN OTRO LADO, 
                # pero generalmente es seguro si confías en checkout.session.completed)
                # Si no existe, mejor retornar 200 y revisar el log.
                print(f"Advertencia: No se encontró la Subscription con customer ID {stripe_customer_id}.")
                return HttpResponse(status=200)

            # Actualizar la suscripción existente
            subscription.stripe_subscription_id = stripe_subscription_id
            subscription.status = stripe_sub["status"]
            subscription.current_period_end = current_period_end # ✅ Sincroniza la fecha en Subscription
            subscription.plan_type = plan_type
            subscription.save()

            # 2. Guardar/Actualizar en CustomUser
            user = subscription.user
            user.is_vip = subscription.status == "active" 
            user.subscription_expires_at = current_period_end # ✅ Sincroniza la fecha en CustomUser
            user.save()
            
        except Exception as e:
            print(f"Error al actualizar suscripción/usuario en webhook: {e}")
            return HttpResponse(status=500)

        return HttpResponse(status=200)

    # 3. BLOQUES ELIMINADOS
    # Se elimina 'invoice.payment_succeeded' para evitar conflictos de fechas.

    return HttpResponse(status=200)



@csrf_exempt
def member_area(request):
    """
    Verifica si el usuario tiene acceso VIP.
    """
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

    # Fecha expirada: Comprobar si la fecha de expiración ha pasado
    # Se usa timezone.now() para comparar fechas 'aware' (con zona horaria)
    if user.subscription_expires_at and user.subscription_expires_at < timezone.now():
        
        # Desactivar la membresía si expiró
        user.is_vip = False
        user.subscription_expires_at = None
        user.save()
        
        return JsonResponse({"error": "Tu suscripción expiró"}, status=403)

    return JsonResponse({"message": "Bienvenido a la zona VIP 🚀"})