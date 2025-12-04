from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Avg, Sum, F
from django.db.models.functions import TruncDate
from django.utils.timezone import now, timedelta
from django.http import JsonResponse
from accounts.models import Estudiante
from core.models import Carrera, Materia, Unidad
from ejercicios.models import Intento, Ejercicio, TipoEjercicio
from django.contrib import messages
from .forms import UploadExcelForm
from .utils.excel_handler import ExcelEjerciciosHandler
import json


@login_required
def dashboard_profesor(request):
    """
    Dashboard principal para profesores con métricas y análisis
    """
    
    # Filtros
    carrera_id = request.GET.get("carrera_id")
    materia_id = request.GET.get("materia_id")
    
    
    carreras = Carrera.objects.all()
    materias = Materia.objects.all()

    context = {
        "carreras": carreras,
        "materias": materias,
        "selected_carrera": None,
        "selected_materia": None,
        
        # Métricas generales
        "total_estudiantes": 0,
        "total_intentos_general": 0,
        "promedio_general_accuracy": 0,
        "promedio_tiempo_general": 0,

        # Data tablas
        "students": [],

        # Data gráficos (inicializados como JSON vacío)
        "chart_labels": json.dumps([]),
        "chart_intentos": json.dumps([]),
        "chart_accuracy": json.dumps([]),
        "chart_correctos": json.dumps([]),
        "chart_incorrectos": json.dumps([]),
        "chart_tiempo": json.dumps([]),
        "chart_dificultad": json.dumps([]),
        "chart_tipos_labels": json.dumps([]),
        "chart_tipos_count": json.dumps([]),
        "chart_intentos_por_dia_labels": json.dumps([]),
        "chart_intentos_por_dia_data": json.dumps([]),
        "chart_distribucion_dificultad_labels": json.dumps([]),
        "chart_distribucion_dificultad_data": json.dumps([]),
    }

    # Si no hay filtros, no mostrar datos
    if not carrera_id and not materia_id:
        # print("DEBUG - No hay filtros, retornando vista vacía")
        return render(request, "dashboard/dashboard.html", context)

    # Construir query de estudiantes
    estudiantes_query = Estudiante.objects.select_related("user", "carrera")
    
    if carrera_id:
        carrera = get_object_or_404(Carrera, pk=carrera_id)
        context["selected_carrera"] = carrera
        estudiantes_query = estudiantes_query.filter(carrera=carrera)
        # print(f"DEBUG - Carrera seleccionada: {carrera.nombre}")
    
    if materia_id:
        materia = get_object_or_404(Materia, pk=materia_id)
        context["selected_materia"] = materia
        # print(f"DEBUG - Materia seleccionada: {materia.nombre}")

    # Query base de intentos con filtros
    intentos_filter = Q()
    if materia_id:
        intentos_filter &= Q(intento__ejercicio__materia_id=materia_id)

    # Anotar estudiantes con métricas
    estudiantes = estudiantes_query.annotate(
        total_intentos=Count("intento", filter=intentos_filter),
        total_correctos=Count(
            "intento", 
            filter=intentos_filter & Q(intento__es_correcto=True)
        ),
        total_incorrectos=Count(
            "intento", 
            filter=intentos_filter & Q(intento__es_correcto=False)
        ),
        accuracy=Avg("intento__puntos", filter=intentos_filter),
        tiempo_promedio=Avg("intento__tiempo_en_segundos", filter=intentos_filter),
        dificultad_promedio=Avg("intento__ejercicio__dificultad", filter=intentos_filter),
    ).filter(total_intentos__gt=0).order_by('-total_intentos')

    # print(f"DEBUG - Total estudiantes con intentos: {estudiantes.count()}")

    # Procesar datos de estudiantes
    students_data = []
    chart_labels = []
    chart_intentos = []
    chart_accuracy = []
    chart_correctos = []
    chart_incorrectos = []
    chart_tiempo = []
    chart_dificultad = []
    
    total_accuracy_sum = 0
    total_intentos_count = 0
    total_tiempo_sum = 0

    for est in estudiantes:
        # Calcular porcentajes
        pct_correctos = round((est.total_correctos / est.total_intentos) * 100, 2) if est.total_intentos > 0 else 0
        accuracy_val = round((est.accuracy or 0) * 100, 2)
        tiempo_prom = round(est.tiempo_promedio or 0, 2)
        dificultad_prom = round(est.dificultad_promedio or 0, 2)

        students_data.append({
            "id": est.id,
            "username": est.user.username,
            "first_name": est.user.first_name,
            "last_name": est.user.last_name,
            "email": est.user.email,
            "semestre_actual": est.semestre_actual,
            "total_intentos": est.total_intentos,
            "total_correctos": est.total_correctos,
            "total_incorrectos": est.total_incorrectos,
            "porcentaje_correctos": pct_correctos,
            "accuracy_promedio": accuracy_val,
            "tiempo_promedio": tiempo_prom,
            "dificultad_promedio": dificultad_prom,
        })

        # Acumular totales
        total_accuracy_sum += accuracy_val
        total_intentos_count += est.total_intentos
        total_tiempo_sum += tiempo_prom

        # Datos para gráficos
        nombre_completo = f"{est.user.first_name} {est.user.last_name}"
        chart_labels.append(nombre_completo)
        chart_intentos.append(est.total_intentos)
        chart_accuracy.append(accuracy_val)
        chart_correctos.append(est.total_correctos)
        chart_incorrectos.append(est.total_incorrectos)
        chart_tiempo.append(tiempo_prom)
        chart_dificultad.append(dificultad_prom)

    context["students"] = students_data
    context["total_estudiantes"] = len(students_data)
    context["total_intentos_general"] = total_intentos_count
    
    if len(students_data) > 0:
        context["promedio_general_accuracy"] = round(total_accuracy_sum / len(students_data), 2)
        context["promedio_tiempo_general"] = round(total_tiempo_sum / len(students_data), 2)

    # print(f"DEBUG - Total estudiantes procesados: {len(students_data)}")
    # print(f"DEBUG - Total intentos: {total_intentos_count}")

    # Serializar datos de gráficos de estudiantes
    context["chart_labels"] = json.dumps(chart_labels)
    context["chart_intentos"] = json.dumps(chart_intentos)
    context["chart_accuracy"] = json.dumps(chart_accuracy)
    context["chart_correctos"] = json.dumps(chart_correctos)
    context["chart_incorrectos"] = json.dumps(chart_incorrectos)
    context["chart_tiempo"] = json.dumps(chart_tiempo)
    context["chart_dificultad"] = json.dumps(chart_dificultad)

    # -------------------------------
    # 📊 DISTRIBUCIÓN POR TIPO DE EJERCICIO
    # -------------------------------
    if carrera_id or materia_id:
        tipos_query = TipoEjercicio.objects.annotate(
            total=Count("ejercicio__intento", distinct=True)
        )
        
        if materia_id:
            tipos_query = tipos_query.filter(ejercicio__materia_id=materia_id)
        if carrera_id:
            tipos_query = tipos_query.filter(ejercicio__intento__estudiante__carrera_id=carrera_id)
        
        tipos = tipos_query.filter(total__gt=0).order_by('-total')

        chart_tipos_labels = [t.get_tipo_ejercicio_display() for t in tipos]
        chart_tipos_count = [t.total for t in tipos]
        
        # print(f"DEBUG - Tipos encontrados: {len(tipos)}")
        
        context["chart_tipos_labels"] = json.dumps(chart_tipos_labels)
        context["chart_tipos_count"] = json.dumps(chart_tipos_count)

    # -------------------------------
    # 📊 INTENTOS POR DÍA (últimos 30 días)
    # -------------------------------
    if carrera_id or materia_id:
        hace_30_dias = now() - timedelta(days=30)
        
        intentos_query = Intento.objects.filter(fecha_intento__gte=hace_30_dias)
        
        if carrera_id:
            intentos_query = intentos_query.filter(estudiante__carrera_id=carrera_id)
        if materia_id:
            intentos_query = intentos_query.filter(ejercicio__materia_id=materia_id)
        
        intentos_por_dia = (
            intentos_query
            .annotate(dia=TruncDate('fecha_intento'))
            .values('dia')
            .annotate(total=Count('id'))
            .order_by('dia')
        )

        chart_intentos_por_dia_labels = []
        chart_intentos_por_dia_data = []
        
        for d in intentos_por_dia:
            chart_intentos_por_dia_labels.append(d["dia"].strftime("%Y-%m-%d"))
            chart_intentos_por_dia_data.append(d["total"])
        
        # print(f"DEBUG - Días con actividad: {len(chart_intentos_por_dia_labels)}")
        
        context["chart_intentos_por_dia_labels"] = json.dumps(chart_intentos_por_dia_labels)
        context["chart_intentos_por_dia_data"] = json.dumps(chart_intentos_por_dia_data)

    # -------------------------------
    # 📊 DISTRIBUCIÓN DE DIFICULTAD
    # -------------------------------
    if carrera_id or materia_id:
        rangos_dificultad = [
            {"label": "Muy Fácil (-3 a -2)", "min": -3.0, "max": -2.0},
            {"label": "Fácil (-2 a -1)", "min": -2.0, "max": -1.0},
            {"label": "Intermedio (-1 a 0)", "min": -1.0, "max": 0.0},
            {"label": "Medio (0 a 1)", "min": 0.0, "max": 1.0},
            {"label": "Difícil (1 a 2)", "min": 1.0, "max": 2.0},
            {"label": "Muy Difícil (2 a 3)", "min": 2.0, "max": 3.0},
        ]

        chart_distribucion_dificultad_labels = []
        chart_distribucion_dificultad_data = []
        
        intentos_dificultad_query = Intento.objects.all()
        
        if carrera_id:
            intentos_dificultad_query = intentos_dificultad_query.filter(
                estudiante__carrera_id=carrera_id
            )
        if materia_id:
            intentos_dificultad_query = intentos_dificultad_query.filter(
                ejercicio__materia_id=materia_id
            )

        for rango in rangos_dificultad:
            count = intentos_dificultad_query.filter(
                ejercicio__dificultad__gte=rango["min"],
                ejercicio__dificultad__lt=rango["max"]
            ).count()
            
            if count > 0:
                chart_distribucion_dificultad_labels.append(rango["label"])
                chart_distribucion_dificultad_data.append(count)
        
        # print(f"DEBUG - Rangos de dificultad con datos: {len(chart_distribucion_dificultad_labels)}")
        
        context["chart_distribucion_dificultad_labels"] = json.dumps(chart_distribucion_dificultad_labels)
        context["chart_distribucion_dificultad_data"] = json.dumps(chart_distribucion_dificultad_data)

    # print("DEBUG - Renderizando template")
    return render(request, "dashboard/dashboard.html", context)


@login_required
def upload_ejercicios_view(request):
    """Vista para cargar ejercicios masivamente desde Excel"""
    
    if request.method == 'POST':
        form = UploadExcelForm(request.POST, request.FILES)
        
        if form.is_valid():
            materia_id = form.cleaned_data['materia'].id
            archivo = request.FILES['archivo_excel']
            
            # Intentar obtener el docente (opcional)
            docente = None
            try:
                docente = request.user.docente
            except:
                pass
            
            # Procesar el archivo
            ejercicios_creados, errores = ExcelEjerciciosHandler.procesar_excel(
                archivo, 
                materia_id, 
                docente
            )
            
            # Mostrar resultados
            if ejercicios_creados > 0:
                messages.success(
                    request, 
                    f'✅ Se crearon {ejercicios_creados} ejercicios correctamente.'
                )
            
            if errores:
                for error in errores[:10]:  # Mostrar máximo 10 errores
                    messages.warning(request, f'⚠️ {error}')
                
                if len(errores) > 10:
                    messages.warning(
                        request, 
                        f'⚠️ Y {len(errores) - 10} errores más...'
                    )
            
            if ejercicios_creados > 0:
                return redirect('profesor:upload_ejercicios')
    
    else:
        form = UploadExcelForm()
    
    # Obtener todas las materias para el selector
    materias = Materia.objects.all().order_by('nombre')
    
    context = {
        'form': form,
        'materias': materias,
        'titulo': 'Carga Masiva de Ejercicios'
    }
    
    return render(request, 'dashboard/upload_ejercicios.html', context)


@login_required
def descargar_plantilla_view(request):
    """Descarga la plantilla Excel para cargar ejercicios"""
    
    materia_id = request.GET.get('materia_id')
    
    if not materia_id:
        messages.error(request, 'Debes seleccionar una materia primero')
        return redirect('profesor:upload_ejercicios')
    
    try:
        return ExcelEjerciciosHandler.generar_plantilla(materia_id)
    except Exception as e:
        messages.error(request, f'Error al generar plantilla: {str(e)}')
        return redirect('profesor:upload_ejercicios')


@login_required
def get_unidades_por_materia(request):
    """
    API endpoint para obtener las unidades de una materia específica
    Retorna JSON con las unidades
    """
    materia_id = request.GET.get('materia_id')
    
    if not materia_id:
        return JsonResponse({'error': 'materia_id es requerido'}, status=400)
    
    try:
        unidades = Unidad.objects.filter(materia_id=materia_id).order_by('num_unidad')
        
        unidades_data = [
            {
                'id': unidad.id,
                'num_unidad': unidad.num_unidad,
                'nombre': unidad.nombre,
                'objetivo': unidad.objetivo or ''
            }
            for unidad in unidades
        ]
        
        return JsonResponse({
            'success': True,
            'unidades': unidades_data,
            'total': len(unidades_data)
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)