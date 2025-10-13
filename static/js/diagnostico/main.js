import { submitAnswer } from './network.js';
import { CountdownTimer } from './timer.js';
import { bindStepButtons, updateTimeDisplay, resetStepsContainer } from './ui-controllers.js';

document.addEventListener('DOMContentLoaded', () => {
  const root = document.getElementById('diagnostico-root');
  const timeElement = document.querySelector('.time');
  const enunciadoElement = document.getElementById('enunciado');
  const stepsContainer = document.getElementById('steps-container');
  const addStepBtn = document.getElementById('add-step-btn');
  const removeStepBtn = document.getElementById('remove-step-btn');
  const finalizeBtn = document.getElementById('finalize-btn');
  const ejercicioIdInput = document.getElementById('ejercicio-id');

  bindStepButtons({ addBtn: addStepBtn, removeBtn: removeStepBtn, stepsContainer });

  // leer segundos restantes enviados por el servidor (data-remaining-seconds -> dataset.remainingSeconds)
  const remainingFromServer = parseInt(root.dataset.remainingSeconds || '0', 10);
  let timer = null;

  function startTimerFromPageLoad() {
    if (isNaN(remainingFromServer) || remainingFromServer < 0) {
      console.error("Error: tiempo restante inválido en data-remaining-seconds.");
      window.location.href = '/';
      return;
    }

    if (remainingFromServer === 0) {
      // Si ya está vencido al cargar la página
      handleTimeUp();
      return;
    }

    timer = new CountdownTimer({
      remainingSeconds: remainingFromServer,
      onTick: (remaining) => updateTimeDisplay(timeElement, remaining),
      onFinish: () => handleTimeUp()
    });
    timer.start();
  }

  function handleTimeUp() {
    try {
      alert('Tiempo agotado. Se finalizará el diagnóstico.');
    } finally {
      window.location.href = '/';
    }
  }

  async function enviarRespuesta() {
    finalizeBtn.disabled = true;
    let pasos;
    try {
      pasos = Array.from(stepsContainer.getElementsByClassName('step-input'))
        .map(el => el.value.trim())
        .filter(v => v);
      if (pasos.length === 0) {
        alert('Completa al menos un paso.');
        return;
      }
    } finally {
      finalizeBtn.disabled = false;
    }

    // valor público y fiable desde el timer del cliente (indicativo)
    const remainingClient = timer ? timer.getRemainingSeconds() : 0;

    const payload = {
      ejercicio_id: parseInt(ejercicioIdInput.value, 10),
      respuesta_estudiante: pasos[pasos.length - 1],
      tiempo_en_segundos: remainingClient,   // compatibilidad legacy
      remaining_seconds: remainingClient,    // campo explícito interpretado por backend
      pasos: pasos
    };

    try {
      const data = await submitAnswer(payload);
      if (data.success && !data.final) {
        resetStepsContainer(stepsContainer);
        if (data.contexto?.display_text) {
          enunciadoElement.textContent = data.contexto.display_text;
          const hintP = document.querySelector('.hint-text p');
          if (hintP) hintP.textContent = data.contexto.hint || '';
          ejercicioIdInput.value = data.ejercicio.id;
        }
      } else {
        alert(data.motivo || 'Diagnóstico finalizado.');
        window.location.href = '/';
      }
    } catch (e) {
      console.error('submitAnswer error', e);
      alert('No se pudo enviar la respuesta.');
    }
  }

  finalizeBtn.addEventListener('click', enviarRespuesta);

  startTimerFromPageLoad();
});
