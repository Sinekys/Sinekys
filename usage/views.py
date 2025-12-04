from rest_framework.decorators import api_view
from rest_framework.response import Response
from ejercicios.models import Intento
from usage.services import can_user_attempt, register_attempt


@api_view(["POST"])
def registrar_intento(request):
    user = request.user  # estudiante autenticado

    # 1. Verificar límite diario
    ok, limit, count = can_user_attempt(user)
    if not ok:
        return Response({
            "detail": "Has alcanzado tu límite diario",
            "limit": limit,
            "used": count
        }, status=403)

    estudiante_id = request.data.get("estudiante_id")
    ejercicio_id = request.data.get("ejercicio_id")

    # 2. Verificar límite de 3 intentos por ejercicio
    intentos_previos = Intento.objects.filter(
        estudiante_id=estudiante_id,
        ejercicio_id=ejercicio_id
    ).count()

    if intentos_previos >= 3:
        return Response(
            {"detail": "Has llegado al máximo de 3 intentos para este ejercicio"},
            status=403
        )

    # 3. Crear el intento
    intento = Intento.objects.create(
        estudiante_id=estudiante_id,
        ejercicio_id=ejercicio_id,
        respuesta_estudiante=request.data.get("respuesta_estudiante"),
        es_correcto=False,
        puntos=0,
        tiempo_en_segundos=0,
    )

    # 4. Registrar intento en la cuota diaria
    new_count = register_attempt(user)

    return Response({
        "success": True,
        "attempts_today": new_count,
        "remaining_attempts_for_exercise": 3 - (intentos_previos + 1),
        "intento_id": intento.id
    })
