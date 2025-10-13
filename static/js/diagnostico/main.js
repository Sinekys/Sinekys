// static/js/diagnostico/main.js

import { submitAnswer } from './network.js';
import { CountdownTimer } from './timer.js';
import { bindStepButtons, updateTimeDisplay, resetStepsContainer } from './ui-controllers.js';

document.addEventListener('DOMContentLoaded', () => {
  const root = document.getElementById('diagnostico-root');
  const durationDefault = parseInt(root.dataset.duration || '3540', 10); // 59 min
  const timeElement = document.querySelector('.time');
  const enunciadoElement = document.getElementById('enunciado');
  const stepsContainer = document.getElementById('steps-container');
  const addStepBtn = document.getElementById('add-step-btn');
  const removeStepBtn = document.getElementById('remove-step-btn');
  const finalizeBtn = document.getElementById('finalize-btn');
  const ejercicioIdInput = document.getElementById('ejercicio-id');

  bindStepButtons({addBtn: addStepBtn, removeBtn: removeStepBtn, stepsContainer});

  let timer = null;

  
  function startTimerFromPageLoad() {
    const fechaInicioIso = root.dataset.fechaInicio;
    const duracionSegundos = parseInt(root.dataset.duracion, 10) || 3540;

    if (!fechaInicioIso){
      alert("Error: no se pudo determinr cuando comenzó la prueba x_X");
      window.location.href = '/';
      return
    }
    const fechaInicio = new Date(fechaInicioIso);
    const endTime = new Date(fechaInicio.getTime() + duracionSegundos * 1000);
    startTimerWithServerInfo(fechaInicio.toISOString(), endTime.toISOString());
  }

  function startTimerWithServerInfo(serverNowIso, endTimeIso) {
    if (timer) timer.stop();
    timer = new CountdownTimer({
      serverNowIso,
      endTimeIso,
      onTick: (remaining) => updateTimeDisplay(timeElement, remaining),
      onFinish: () => handleTimeUp()
    });
    timer.start();
  }

  async function handleTimeUp() {
    alert('Tiempo agotado. Se finalizará el diagnóstico.');
    window.location.href = '/';
  }

  async function enviarRespuesta() {
    finalizeBtn.disabled= true;
    let ejerciciosId;
    let pasos;
    try{
      ejerciciosId = ejercicioIdInput.value;
      pasos = Array.from(stepsContainer.getElementsByClassName('step-input'))
                        .map(el => el.value.trim())
                        .filter(v => v);
      if (pasos.length === 0) {
        alert('Completa al menos un paso.');
        return;
      }
    }finally{
      finalizeBtn.disabled = false
    }

    const remaining = timer ? timer._remainingSeconds() : 0;

    const payload = {
      ejercicio_id: parseInt(ejerciciosId, 10),
      respuesta_estudiante: pasos[pasos.length - 1],
      tiempo_en_segundos: remaining,
      pasos: pasos
    };

    try {
      const data = await submitAnswer(payload);
      if (data.success && !data.final) {
        resetStepsContainer(stepsContainer);
        // Actualizar enunciado con la respuesta del backend
        if (data.contexto?.display_text) {
          enunciadoElement.textContent = data.contexto.display_text;
          document.querySelector('.hint-text p').textContent = data.contexto.hint || '';
          ejercicioIdInput.value = data.ejercicio.id;
        }
        // ✅ El temporizador sigue corriendo (no se reinicia)
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