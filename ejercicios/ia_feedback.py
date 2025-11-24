from typing import Optional,Dict, Any, List
from django.db import transaction
from ejercicios.models import Feedback, FeedbackPasos, TipoFeedback, Intento

@transaction.atomic
def save_ai_feedback_intento(
    intento:Intento,
    contexto_ia: Optional[str],
    feedback_json:Optional[Dict[str, Any]] = None,
    fuente: str='chatgpt',
    pasos_feedback: Optional[List[Dict[str,Any]]] = None
    ) -> Feedback:
    fb = Feedback.objects.create(
        intento=intento,
        contexto_ejercicio = (contexto_ia or ""),
        feedback = feedback_json or {},
        fuente_ia=fuente
    )
    
    if pasos_feedback:
        for idx, paso in enumerate(pasos_feedback, start=1):
            tipo_nombre = paso.get("tipo")
            if tipo_nombre:
                tipo_obj, _ = TipoFeedback.objects.get_or_create(nombre=tipo_nombre)
                FeedbackPasos.objects.create(
                    feedback=fb,
                    tipo_feedback=tipo_obj,
                    orden=idx,
                    contenido=paso.get("contenido", ""),
                    datos_aux=paso.get("datos_aux", {})
                )
    return fb
