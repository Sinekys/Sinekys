// static/js/diagnostico/ui-controllers.js
import { formatSeconds } from './utils.js';

export function bindStepButtons({addBtn, removeBtn, stepsContainer}){
  addBtn.addEventListener('click', () => {
    const newInput = document.createElement('input');
    newInput.type = 'text';
    newInput.name = 'step[]';
    newInput.classList.add('step-input');
    newInput.placeholder = 'Nuevo paso';
    newInput.autofocus = true;
    stepsContainer.appendChild(newInput);
  });
  removeBtn.addEventListener('click', () => {
    const stepInputs = stepsContainer.getElementsByClassName('step-input');
    if (stepInputs.length > 1) {
      stepsContainer.removeChild(stepInputs[stepInputs.length - 1]);
    }
  });
}

export function updateTimeDisplay(el, seconds){
  el.textContent = `Tiempo: ${formatSeconds(seconds)}`;
}

export function resetStepsContainer(container){
  container.innerHTML = `<input type="text" name="step[]" class="step-input" placeholder="Empieza aquí ^^" autofocus>`;
}
