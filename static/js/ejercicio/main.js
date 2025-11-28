// static/js/ejercicio/main.js
import { submitAnswer } from "../diagnostico/network.js";
import { resetStepsContainer, bindStepButtons } from "../diagnostico/ui-controllers.js";

document.addEventListener('DOMContentLoaded', () => {
  const root = document.getElementById('ejercicio-root'); // añade este contenedor en la plantilla
  // fallback: si no existe root, usa location.href como postUrl
  const postUrl = root?.dataset.postUrl || window.location.href;

  const finalizeBtn = document.getElementById('finalize-btn');
  const ejercicioIdInput = document.getElementById('ejercicio-id');
  const stepsContainer = document.getElementById('steps-container');
  const enunciadoElement = document.getElementById('enunciado');
  const addStepBtn = document.getElementById('add-step-btn');
  const removeStepBtn = document.getElementById('remove-step-btn');

  if (!finalizeBtn || !ejercicioIdInput || !stepsContainer) {
    console.error("Elementos críticos no encontrados en la página (finalize-btn, ejercicio-id o steps-container).");
    return;
  }

  // habilitar botones de pasos
  bindStepButtons({ addBtn: addStepBtn, removeBtn: removeStepBtn, stepsContainer });

  finalizeBtn.addEventListener('click', async () => {
    finalizeBtn.disabled = true;
    try {
      const pasos = Array.from(stepsContainer.getElementsByClassName('step-input'))
                        .map(el => el.value.trim())
                        .filter(v => v);

      if (pasos.length === 0) {
        alert('Completa al menos un paso.');
        finalizeBtn.disabled = false;
        return;
      }

      const payload = {
        ejercicio_id: parseInt(ejercicioIdInput.value, 10),
        // usamos el campo 'respuesta' porque tu view espera 'respuesta' en modo normal
        respuesta: pasos[pasos.length - 1],
        pasos: pasos
      };

      // usamos submitAnswer que ya maneja CSRF desde cookie (network.js)
      const data = await submitAnswer(payload, postUrl);

      if (data.success) {
        // limpiar UI local
        resetStepsContainer(stepsContainer);

        // si el servidor devuelve redirect_url la usamos (siempre priorizarlo)
        if (data.redirect_url) {
          window.location.href = data.redirect_url;
          return;
        }

        // fallback: si sólo viene intento_id intentamos construir URL conocida
        if (data.intento_id) {
          // Ajusta el prefijo si tu include de URLs es diferente.
          // En tu proyecto el include es path('ejercicio/', ...), por eso uso /ejercicio/check/
          window.location.href = `/ejercicio/check/${data.intento_id}/`;
          return;
        }

        // si no hay redirect, mostrar mensaje genérico
        alert('Intento guardado.');
        finalizeBtn.disabled = false;
        return;
      } else {
        // si success === false maneja errores
        const msg = data.error || data.motivo || 'No se pudo procesar la respuesta.';
        alert(msg);
        finalizeBtn.disabled = false;
        return;
      }

    } catch (err) {
      console.error('Error submitting answer:', err);
      // mostrar mensaje útil al usuario (no exponer stack)
      alert('Ocurrió un error al enviar la respuesta. Por favor, intenta nuevamente.');
      finalizeBtn.disabled = false;
    }
  });
});
