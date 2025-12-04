// static/js/ejercicio/main.js
import { submitAnswer } from "../diagnostico/network.js";
import { resetStepsContainer, bindStepButtons } from "../diagnostico/ui-controllers.js";

document.addEventListener('DOMContentLoaded', () => {
  const root = document.getElementById('ejercicio-root');
  const postUrl = root?.dataset.postUrl || window.location.href;

  const finalizeBtn = document.getElementById('finalize-btn');
  const ejercicioIdInput = document.getElementById('ejercicio-id');
  const stepsContainer = document.getElementById('steps-container');
  const hintToggle = document.getElementById('hint-toggle');
  const hintText = document.getElementById('hint-text');
  const addStepBtn = document.getElementById('add-step-btn');
  const removeStepBtn = document.getElementById('remove-step-btn');
  const sendingPopup = document.getElementById('sending-popup');

  if (!finalizeBtn || !ejercicioIdInput || !stepsContainer) {
    console.error("Elementos críticos no encontrados en la página (finalize-btn, ejercicio-id o steps-container).");
    return;
  }

  // Función para mostrar el popup de envío
  const showSendingPopup = () => {
    if (sendingPopup) {
      sendingPopup.classList.remove('hidden');
      document.body.style.overflow = 'hidden'; // Evitar scroll mientras el popup está activo
    }
  };

  // Función para ocultar el popup de envío
  const hideSendingPopup = () => {
    if (sendingPopup) {
      sendingPopup.classList.add('hidden');
      document.body.style.overflow = 'auto'; // Restaurar scroll
    }
  };

  // Normalizar estilo de inputs (para los que se agreguen dinámicamente)
  const normalizeInput = (inputEl) => {
    if (!inputEl) return;
    if (!(inputEl instanceof HTMLInputElement || inputEl instanceof HTMLTextAreaElement)) return;
    
    inputEl.classList.add(
      'step-input', 'w-full', 'p-3', 'text-base', 'rounded-md', 
      'border', 'border-gray-700', 'bg-gray-900', 'text-gray-100', 
      'placeholder-gray-400', 'focus:outline-none', 'focus:ring-2', 'focus:ring-orange-500'
    );
    
    if (!inputEl.placeholder) inputEl.placeholder = 'Siguiente paso...';
  };

  // Normalizar inputs existentes
  stepsContainer.querySelectorAll('input, textarea').forEach(el => normalizeInput(el));

  // Observer para nuevos inputs
  const mo = new MutationObserver(mutations => {
    for (const m of mutations) {
      for (const node of m.addedNodes) {
        if (node.nodeType !== 1) continue;
        if (node.querySelectorAll) {
          node.querySelectorAll('input, textarea').forEach(i => normalizeInput(i));
        }
        if (node.tagName === 'INPUT' || node.tagName === 'TEXTAREA') normalizeInput(node);
      }
    }
  });
  
  mo.observe(stepsContainer, { childList: true, subtree: true });

  // Toggle para la pista
  if (hintToggle && hintText) {
    hintToggle.addEventListener('click', () => {
      hintText.classList.toggle('hidden');
      hintToggle.textContent = hintText.classList.contains('hidden') ? '¿Pista?' : 'Ocultar pista';
      
      // Si se muestra la pista, hacer scroll hacia ella
      if (!hintText.classList.contains('hidden')) {
        setTimeout(() => {
          const hintBox = hintText.closest('.hint-box');
          if (hintBox) {
            hintBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
          }
        }, 300);
      }
    });
  }

  // Habilitar botones de pasos
  if (addStepBtn && removeStepBtn) {
    bindStepButtons({ addBtn: addStepBtn, removeBtn: removeStepBtn, stepsContainer });
  }

  // Finalizar ejercicio
  finalizeBtn.addEventListener('click', async () => {
    finalizeBtn.disabled = true;
    finalizeBtn.classList.add('opacity-75', 'cursor-wait');
    
    // Mostrar popup de envío
    showSendingPopup();
    
    try {
      const pasos = Array.from(stepsContainer.getElementsByClassName('step-input'))
                        .map(el => el.value.trim())
                        .filter(v => v);

      if (pasos.length === 0) {
        alert('Completa al menos un paso.');
        finalizeBtn.disabled = false;
        finalizeBtn.classList.remove('opacity-75', 'cursor-wait');
        hideSendingPopup();
        return;
      }

      const payload = {
        ejercicio_id: parseInt(ejercicioIdInput.value, 10),
        respuesta: pasos[pasos.length - 1],
        pasos: pasos
      };

      const data = await submitAnswer(payload, postUrl);

      if (data.success) {
        resetStepsContainer(stepsContainer);
        
        // El popup permanecerá visible durante la redirección
        if (data.redirect_url) {
          window.location.href = data.redirect_url;
          return;
        }

        if (data.intento_id) {
          window.location.href = `/ejercicio/check/${data.intento_id}/`;
          return;
        }

        alert('Intento guardado.');
      } else {
        const msg = data.error || data.motivo || 'No se pudo procesar la respuesta.';
        alert(msg);
      }
    } catch (err) {
      console.error('Error submitting answer:', err);
      alert('Ocurrió un error al enviar la respuesta. Por favor, intenta nuevamente.');
    } finally {
      finalizeBtn.disabled = false;
      finalizeBtn.classList.remove('opacity-75', 'cursor-wait');
      
      // Ocultar el popup solo si no hay redirección
      setTimeout(() => {
        hideSendingPopup();
      }, 300);
    }
  });

  // Scroll automático al último input cuando se agrega un nuevo paso
  if (addStepBtn) {
    addStepBtn.addEventListener('click', () => {
      setTimeout(() => {
        const container = document.querySelector('.inputs');
        if (container) {
          container.scrollTop = container.scrollHeight;
        }
      }, 100);
    });
  }

  // Navegación con teclado
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && document.activeElement.classList.contains('step-input')) {
      e.preventDefault();
      const inputs = document.querySelectorAll('.step-input');
      const currentIndex = Array.from(inputs).indexOf(document.activeElement);
      
      if (currentIndex === inputs.length - 1) {
        // Si está en el último input, crear uno nuevo y enfocarlo
        addStepBtn.click();
        setTimeout(() => {
          const newInputs = document.querySelectorAll('.step-input');
          newInputs[newInputs.length - 1].focus();
        }, 150);
      } else {
        // Si no es el último, enfocar el siguiente
        inputs[currentIndex + 1].focus();
      }
    }
  });
});