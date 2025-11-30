from django.shortcuts import render, get_object_or_404
from django.db.models import Count, Avg, Max, Q, F
from django.http import JsonResponse
from core.models import Carrera, Materia,CarreraMateria
from accounts.models import Estudiante
from django.contrib.auth.decorators import login_required

@login_required
def dashboard_profesor(request):
    """
    Vista principal del dashboard del docente.
    Parámetros GET (opcionales):
        - carrera_id
        - materia_id
    Si no se envían, muestra un resumen general.
    """
    carrera_id = request.GET.get('carrera_id')
    materia_id = request.GET.get('materia_id')

    carreras = Carrera.objects.all()
    materias = Materia.objects.all()

    context = {
        'carreras': carreras,
        'materias': materias,
        'selected_carrera': None,
        'selected_materia': None,
        'students_data': [],
        'summary': {},
    }

    if carrera_id and materia_id:
        carrera = get_object_or_404(Carrera, pk=carrera_id)
        materia = get_object_or_404(Materia, pk=materia_id)
        context['selected_carrera'] = carrera
        context['selected_materia'] = materia

        # Averiguar el/los semestres de la relación carrera-materia
        cm_qs = CarreraMateria.objects.filter(carrera=carrera, materia=materia)
        semestres = list(cm_qs.values_list('semestre', flat=True))

        # Tomaremos estudiantes que están en la misma carrera y cuyo semestre_actual
        # esté dentro de los semestres relacionados
        estudiantes_qs = Estudiante.objects.filter(
            carrera=carrera,
            semestre_actual__in=semestres
        ).select_related('user')

        # Anotar métricas de intentos por estudiante
        estudiantes_annot = estudiantes_qs.annotate(
            total_intentos=Count('intentos'),
            total_aciertos=Count('intentos', filter=Q(intentos__es_correcto=True)),
            avg_tiempo=Avg('intentos__tiempo_en_segundos'),
            last_intento=Max('intentos__fecha_intento')
        )

        students_data = []
        total_attempts = 0
        acc_sum = 0
        students_with_attempts = 0

        for est in estudiantes_annot:
            attempts = est.total_intentos or 0
            correct = est.total_aciertos or 0
            avg_time = est.avg_tiempo or 0
            last_try = est.last_intento
            accuracy = (correct / attempts * 100) if attempts > 0 else None

            if attempts > 0:
                total_attempts += attempts
                acc_sum += accuracy
                students_with_attempts += 1

            students_data.append({
                'estudiante_id': est.id,
                'username': getattr(est.user, 'username', ''),
                'first_name': getattr(est.user, 'first_name', ''),
                'last_name': getattr(est.user, 'last_name', ''),
                'semestre_actual': est.semestre_actual,
                'total_intentos': attempts,
                'total_aciertos': correct,
                'accuracy': round(accuracy, 2) if accuracy is not None else None,
                'avg_tiempo': round(avg_time, 2) if avg_time else None,
                'last_intento': last_try,
            })

        # Resumen global
        summary = {
            'num_estudiantes': estudiantes_qs.count(),
            'total_intentos': total_attempts,
            'promedio_accuracy': round((acc_sum / students_with_attempts), 2) if students_with_attempts else None,
            'students_with_attempts': students_with_attempts,
        }

        context['students_data'] = students_data
        context['summary'] = summary

    return render(request, 'dashboard/dashboard.html', context)


@login_required
def dashboard_data_json(request):
    """
    Endpoint JSON para obtener datos (por ejemplo para Chart.js).
    Debe recibir carrera_id y materia_id por GET.
    """
    carrera_id = request.GET.get('carrera_id')
    materia_id = request.GET.get('materia_id')
    if not (carrera_id and materia_id):
        return JsonResponse({'error': 'falta carrera_id o materia_id'}, status=400)

    carrera = get_object_or_404(Carrera, pk=carrera_id)
    materia = get_object_or_404(Materia, pk=materia_id)
    cm_qs = CarreraMateria.objects.filter(carrera=carrera, materia=materia)
    semestres = list(cm_qs.values_list('semestre', flat=True))

    estudiantes_qs = Estudiante.objects.filter(carrera=carrera, semestre_actual__in=semestres).select_related('user')
    estudiantes_annot = estudiantes_qs.annotate(
        total_intentos=Count('intentos'),
        total_aciertos=Count('intentos', filter=Q(intentos__es_correcto=True))
    )

    labels = []
    accuracies = []
    attempts = []
    for est in estudiantes_annot:
        attempts_count = est.total_intentos or 0
        correct = est.total_aciertos or 0
        accuracy = (correct / attempts_count * 100) if attempts_count > 0 else 0
        username = getattr(est.user, 'username', '') or f"{getattr(est.user, 'first_name','')} {getattr(est.user,'last_name','')}"
        labels.append(username)
        accuracies.append(round(accuracy, 2))
        attempts.append(attempts_count)

    return JsonResponse({
        'labels': labels,
        'accuracies': accuracies,
        'attempts': attempts,
    })
