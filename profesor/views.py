from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from accounts.models import Estudiante
from core.models import Carrera
from ejercicios.models import Intento, Ejercicio, TipoEjercicio
from django.db.models import Count, Q, Avg, Sum
from django.utils.timezone import now, timedelta


@login_required
def dashboard_profesor(request):

    carrera_id = request.GET.get("carrera_id")
    carreras = Carrera.objects.all()

    context = {
        "carreras": carreras,
        "selected_carrera": None,

        # Data tablas
        "students": [],

        # Data gráficos
        "chart_labels": [],
        "chart_intentos": [],
        "chart_accuracy": [],
        "chart_correctos": [],
        "chart_incorrectos": [],

        # Nuevos gráficos
        "chart_tiempo": [],
        "chart_dificultad": [],
        "chart_tipos_labels": [],
        "chart_tipos_count": [],
        "chart_intentos_por_dia_labels": [],
        "chart_intentos_por_dia_data": [],
    }

    if carrera_id:
        carrera = get_object_or_404(Carrera, pk=carrera_id)
        context["selected_carrera"] = carrera

        estudiantes = (
            Estudiante.objects
            .filter(carrera=carrera)
            .select_related("user")
            .annotate(
                total_intentos=Count("intento"),
                total_correctos=Count("intento", filter=Q(intento__es_correcto=True)),
                total_incorrectos=Count("intento", filter=Q(intento__es_correcto=False)),
                accuracy=Avg("intento__puntos"),
                tiempo_promedio=Avg("intento__tiempo_en_segundos"),
                dificultad_promedio=Avg("intento__ejercicio__dificultad"),
            )
        )

        students_data = []

        for est in estudiantes:

            if est.total_intentos > 0:
                pct_correctos = round((est.total_correctos / est.total_intentos) * 100, 2)
            else:
                pct_correctos = 0

            accuracy_val = round((est.accuracy or 0) * 100, 2)

            students_data.append({
                "id": est.id,
                "username": est.user.username,
                "first_name": est.user.first_name,
                "last_name": est.user.last_name,
                "semestre_actual": est.semestre_actual,
                "total_intentos": est.total_intentos,
                "total_correctos": est.total_correctos,
                "total_incorrectos": est.total_incorrectos,
                "porcentaje_correctos": pct_correctos,
                "accuracy_promedio": accuracy_val,
                "tiempo_promedio": round(est.tiempo_promedio or 0, 2),
                "dificultad_promedio": round(est.dificultad_promedio or 0, 2),
            })

            # Charts
            context["chart_labels"].append(f"{est.user.first_name} {est.user.last_name}")
            context["chart_intentos"].append(est.total_intentos)
            context["chart_accuracy"].append(accuracy_val)
            context["chart_correctos"].append(est.total_correctos)
            context["chart_incorrectos"].append(est.total_incorrectos)
            context["chart_tiempo"].append(round(est.tiempo_promedio or 0, 2))
            context["chart_dificultad"].append(round(est.dificultad_promedio or 0, 2))

        context["students"] = students_data

        # -------------------------------
        # 📊 DISTRIBUCIÓN POR TIPO DE EJERCICIO
        # -------------------------------
        tipos = (
            TipoEjercicio.objects
            .annotate(total=Count("ejercicio__intento"))
            .filter(total__gt=0)
        )

        context["chart_tipos_labels"] = [t.tipo_ejercicio for t in tipos]
        context["chart_tipos_count"] = [t.total for t in tipos]

        # -------------------------------
        # 📊 INTENTOS POR DÍA (últimos 7 días)
        # -------------------------------
        hace_7_dias = now() - timedelta(days=7)

        intentos_por_dia = (
            Intento.objects
            .filter(estudiante__carrera=carrera, fecha_intento__gte=hace_7_dias)
            .extra({"day": "DATE(fecha_intento)"})
            .values("day")
            .annotate(total=Count("id"))
            .order_by("day")
        )

        for d in intentos_por_dia:
            context["chart_intentos_por_dia_labels"].append(str(d["day"]))
            context["chart_intentos_por_dia_data"].append(d["total"])

    return render(request, "dashboard/dashboard.html", context)
