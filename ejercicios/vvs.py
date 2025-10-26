
# Este código de mlo dio Copilot, pero hacer que ser repita codigo y aun le falta perfeccionamiento, 
# pero es algo bueno para inspirarse mientras 



# def _prepare_next(self, request, wants_json: bool = False):
#         """
#         Lógica común: obtener estudiante, diagnóstico, siguiente ejercicio y contexto.
#         Devuelve una tupla (error_response, payload). Si error_response es truthy, debe retornarse inmediatamente.
#         """
#         try:
#             estudiante = request.user.estudiante
#         except Estudiante.DoesNotExist:
#             if wants_json:
#                 return (JsonResponse({"error": "Estudiante no encontrado"}, status=400), None)
#             return (HttpResponseBadRequest("Usuario no encontrado"), None)

#         # Diferente validación según si la petición quiere JSON o HTML
#         if wants_json:
#             diag_activo = diagnostico_activo(estudiante)
#             if not diag_activo:
#                 return (JsonResponse({
#                     "error": "El diagnóstico ya finalizó o expiró",
#                     "finalizado": True
#                 }, status=403), None)
#             diagnostico = diag_activo
#         else:
#             diagnostico = obtener_o_validar_diagnostico(estudiante)
#             if diagnostico.finalizado or diagnostico.is_expired():
#                 motivo = 'Tiempo agotado' if diagnostico.is_expired() else 'Precisión alcanzada'
#                 return (render(request, "diagnostico/finalizado.html", {
#                     'diagnostico': diagnostico,
#                     'motivo': motivo
#                 }), None)

#         ejercicio = seleccionar_siguiente_ejercicio(estudiante)
#         if not ejercicio:
#             diagnostico.finalizado = True
#             diagnostico.save(update_fields=['finalizado'])
#             if wants_json:
#                 return (JsonResponse({
#                     "error": "No hay ejercicios disponibles",
#                     "finalizado": True
#                 }, status=200), None)
#             return (render(request, "diagnostico/finalizado.html", {
#                 'diagnostico': diagnostico,
#                 'motivo': 'no hay más ejercicios'
#             }), None)

#         remaining_seconds = max(0, int(diagnostico.tiempo_restante()))
#         contexto = contextualize_exercise_diagnostico(ejercicio)

#         payload = {
#             "estudiante": estudiante,
#             "diagnostico": diagnostico,
#             "ejercicio": ejercicio,
#             "contexto": contexto,
#             "remaining_seconds": remaining_seconds
#         }
#         return (None, payload)


#     def get(self, request):
#         accept = request.headers.get('Accept', '')
#         wants_json = 'application/json' in accept or request.headers.get('X-Requested-With') == 'XMLHttpRequest'

#         err, payload = self._prepare_next(request, wants_json=wants_json)
#         if err:
#             return err

#         if wants_json:
#             ejercicio = payload["ejercicio"]
#             contexto = payload["contexto"]
#             return JsonResponse({
#                 "ejercicio": {
#                     "id": ejercicio.id,
#                     "enunciado": ejercicio.enunciado,
#                     "dificultad": float(ejercicio.dificultad)
#                 },
#                 "contexto": contexto
#             })
#         else:
#             return render(request, "diagnostico/index.html", {
#                 "ejercicio": payload["ejercicio"],
#                 "contexto": payload["contexto"],
#                 "diagnostico": payload["diagnostico"],
#                 "remaining_seconds": payload["remaining_seconds"]
#             })