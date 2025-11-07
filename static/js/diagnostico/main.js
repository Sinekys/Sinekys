import { submitAnswer } from './network.js';
import { CountdownTimer } from './timer.js';
import { bindStepButtons, updateTimeDisplay, resetStepsContainer } from './ui-controllers.js';

document.addEventListener('DOMContentLoaded', () => {
  const root = document.getElementById('diagnostico-root');

  if (!root) {
    console.error('diagnostico-root element not found');
    return;
  }

  const postUrl = root.dataset.postUrl || '/ejercicio/diagnostico/';
  const remainingFromServer = parseInt(root.dataset.remainingSeconds || '0', 10);

  // const durationDefault = parseInt(root.dataset.duration || '3540', 10); // 59 min
  const timeElement = document.querySelector('.time');
  const enunciadoElement = document.getElementById('enunciado');
  const stepsContainer = document.getElementById('steps-container');
  const addStepBtn = document.getElementById('add-step-btn');
  const removeStepBtn = document.getElementById('remove-step-btn');
  const finalizeBtn = document.getElementById('finalize-btn');
  const ejercicioIdInput = document.getElementById('ejercicio-id');

  bindStepButtons({addBtn: addStepBtn, removeBtn: removeStepBtn, stepsContainer});

  let timer = null;

  function startTimerFromRemaining(remainingSeconds) {
    if (timer) timer.stop();
    timer = new CountdownTimer({
      remainingSeconds: remainingSeconds,
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
    try{
      console.log("POST URL:", postUrl);
      const ejercicioId = ejercicioIdInput.value;
      const pasos = Array.from(stepsContainer.getElementsByClassName('step-input'))
                        .map(el => el.value.trim())
                        .filter(v => v);
      if (pasos.length === 0) {
        alert('Completa al menos un paso.');
        return;
      }
    
// Si está actualizadoooo por que me sigue dando erroroorrr
    const remaining = timer ? timer.getRemainingSeconds() : 0;

    const payload = {
      ejercicio_id: parseInt(ejercicioId, 10),
      respuesta_estudiante: pasos[pasos.length - 1],
      tiempo_en_segundos: remaining,
      remaining_seconds: remaining, // backend lo espera
      pasos: pasos
    };

    const data = await submitAnswer(payload, postUrl);
    if (data.success && !data.final) {
        resetStepsContainer(stepsContainer);
        // Actualizar enunciado con la respuesta del backend
        if (data.contexto?.display_text) {
          enunciadoElement.textContent = data.contexto.display_text;

          const hintP = document.querySelector('.hint-text p');
          if (hintP) hintP.textContent = data.contexto.hint || '';
          if (data.ejercicio?.id) ejercicioIdInput.value = data.ejercicio.id;
        }
      } else {
        alert(data.motivo || 'Diagnóstico finalizado.');
        window.location.href = '/';
      }
    } catch (e) {
      console.error('submitAnswer error', e);
      alert('No se pudo enviar la respuesta.');
  } finally{
      finalizeBtn.disabled = false;
  }
}

finalizeBtn.addEventListener('click', enviarRespuesta);

  startTimerFromRemaining(remainingFromServer);
});