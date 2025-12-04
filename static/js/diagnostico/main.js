import { submitAnswer } from './network.js';
import { CountdownTimer } from './timer.js';
import { bindStepButtons, updateTimeDisplay, resetStepsContainer } from './ui-controllers.js';
import { formatSeconds } from './utils.js';

document.addEventListener('DOMContentLoaded', () => {
  const root = document.getElementById('diagnostico-root');
  if (!root) {
    console.error('diagnostico-root element not found');
    return;
  }

  const postUrl = root.dataset.postUrl;
  const remainingFromServer = parseInt(root.dataset.remainingSeconds || '0', 10);
  const timeElement = document.querySelector('.time');
  const enunciadoElement = document.getElementById('enunciado');
  const stepsContainer = document.getElementById('steps-container');
  const hintToggle = document.getElementById('hint-toggle');
  const hintText = document.getElementById('hint-text');
  const addStepBtn = document.getElementById('add-step-btn');
  const removeStepBtn = document.getElementById('remove-step-btn');
  const finalizeBtn = document.getElementById('finalize-btn');
  const ejercicioIdInput = document.getElementById('ejercicio-id');
  const sendingPopup = document.getElementById('sending-popup');
  const headerTitle = document.querySelector('header h1');

  if (!finalizeBtn || !ejercicioIdInput || !stepsContainer) {
    console.error("Elementos críticos no encontrados en la página (finalize-btn, ejercicio-id o steps-container).");
    return;
  }

  // Variables de estado
  let timer = null;
  let currentEjercicioIndex = 1;
  let totalEjercicios = 30; // Valor por defecto, podría venir del backend
  let isProcessing = false;

  // Función para mostrar el popup con animación y contenido personalizado
  const showPopup = (content, options = {}) => {
    const { 
      showCloseButton = false, 
      onClose = null, 
      autoClose = false, 
      closeDelay = 3000,
      backdropClose = true
    } = options;

    if (sendingPopup) {
      // Limpiar contenido anterior
      sendingPopup.innerHTML = '';
      
      // Crear contenedor principal del popup
      const popupContent = document.createElement('div');
      popupContent.className = `bg-gray-900 rounded-2xl p-8 max-w-md w-full mx-4 shadow-2xl transform transition-all ${options.borderColor || 'border-orange-500/30'}`;
      
      if (options.borderColor) {
        popupContent.style.border = `2px solid ${options.borderColor.replace('/30', '')}4D`;
      }

      popupContent.innerHTML = content;
      sendingPopup.appendChild(popupContent);
      
      // Añadir botón de cerrar si se solicita
      if (showCloseButton) {
        const closeButton = document.createElement('button');
        closeButton.className = 'absolute top-4 right-4 text-gray-400 hover:text-white transition';
        closeButton.innerHTML = '<i class="fas fa-times text-xl"></i>';
        closeButton.addEventListener('click', () => {
          sendingPopup.classList.add('hidden');
          document.body.style.overflow = 'auto';
          if (onClose) onClose();
        });
        popupContent.appendChild(closeButton);
      }

      // Mostrar popup con animación
      sendingPopup.classList.remove('hidden');
      document.body.style.overflow = 'hidden';
      
      // Animación de entrada
      popupContent.style.opacity = '0';
      popupContent.style.transform = 'scale(0.95)';
      setTimeout(() => {
        popupContent.style.transition = 'all 0.3s ease-out';
        popupContent.style.opacity = '1';
        popupContent.style.transform = 'scale(1)';
      }, 10);

      // Auto-cerrar si se solicita
      if (autoClose) {
        setTimeout(() => {
          sendingPopup.classList.add('hidden');
          document.body.style.overflow = 'auto';
          if (onClose) onClose();
        }, closeDelay);
      }

      // Permitir cerrar haciendo clic en el fondo
      if (backdropClose) {
        sendingPopup.addEventListener('click', (e) => {
          if (e.target === sendingPopup) {
            sendingPopup.classList.add('hidden');
            document.body.style.overflow = 'auto';
            if (onClose) onClose();
          }
        }, { once: true });
      }
    }
  };

  // Función para actualizar la barra de progreso visual
  const updateProgressBar = (current, total) => {
  // Si ya existe el container, actualizamos sus partes
  const container = document.getElementById('progress-bar-container');

  if (container) {
    const bar = document.getElementById('progress-bar');
    if (bar) bar.style.width = `${(current / total) * 100}%`;

    const currentLabel = container.querySelector('.progress-current');
    const totalLabel = container.querySelector('.progress-total');
    const indexLabel = container.querySelector('.exercise-index');

    if (currentLabel) currentLabel.textContent = current;
    if (totalLabel) totalLabel.textContent = total;
    if (indexLabel) indexLabel.textContent = current;

    return;
  }

  // Si no existe, lo creamos con clases que sí podemos actualizar luego
  const progressBarContainer = document.createElement('div');
  progressBarContainer.id = 'progress-bar-container';
  progressBarContainer.className = 'w-full mt-2';
  progressBarContainer.innerHTML = `
    <div class="flex justify-between text-xs mb-1">
      <span class="text-orange-400 font-medium">
        <span class="progress-label">Ejercicio </span><span class="progress-current">${current}</span>
      </span>
      <span class="text-gray-400">
        <span class="exercise-index">${current}</span> de <span class="progress-total">${total}</span>
      </span>
    </div>
    <div class="w-full bg-gray-800 rounded-full h-2.5">
      <div id="progress-bar" class="bg-orange-500 h-2.5 rounded-full transition-all duration-500" style="width: ${(current/total)*100}%"></div>
    </div>
  `;

  const exerciseElement = document.querySelector('.exercise');
  if (exerciseElement) {
    exerciseElement.parentNode.insertBefore(progressBarContainer, exerciseElement.nextSibling);
  }
};

  // Función para mostrar el popup de carga con progreso
  const showLoadingPopup = (message = 'Cargando siguiente ejercicio', progress = 0) => {
    const progressHtml = progress > 0 ? `
      <div class="w-full bg-gray-800 rounded-full h-2.5 mt-4 mb-2">
        <div class="bg-orange-500 h-2.5 rounded-full transition-all duration-300" style="width: ${progress}%"></div>
      </div>
      <p class="text-orange-400 text-sm font-medium">${progress}% completado</p>
    ` : '';

    showPopup(`
      <div class="flex flex-col items-center text-center">
        <div class="relative mb-6">
          <div class="w-16 h-16 border-4 border-orange-500 border-t-transparent rounded-full animate-spin"></div>
          <div class="absolute inset-0 flex items-center justify-center">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8 text-orange-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
        </div>
        <h3 class="text-2xl font-bold text-orange-400 mb-2">${message}</h3>
        <p class="text-gray-300 text-lg">Por favor, espera mientras procesamos tu respuesta...</p>
        ${progressHtml}
        <div class="mt-4 flex space-x-1">
          <span class="w-2 h-2 bg-orange-400 rounded-full animate-bounce" style="animation-delay: 0s"></span>
          <span class="w-2 h-2 bg-orange-400 rounded-full animate-bounce" style="animation-delay: 0.2s"></span>
          <span class="w-2 h-2 bg-orange-400 rounded-full animate-bounce" style="animation-delay: 0.4s"></span>
        </div>
      </div>
    `, {
      borderColor: 'border-orange-500/30'
    });
  };

  // Función para mostrar popup de tiempo agotado
  const showTimeUpPopup = () => {
    showPopup(`
      <div class="flex flex-col items-center text-center">
        <div class="relative mb-6">
          <div class="w-16 h-16 border-4 border-red-500 border-t-transparent rounded-full animate-spin"></div>
          <div class="absolute inset-0 flex items-center justify-center">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-12 w-12 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
        </div>
        <h3 class="text-2xl font-bold text-red-400 mb-2">¡Tiempo agotado!</h3>
        <p class="text-gray-300 text-lg mb-4">Tu diagnóstico ha finalizado por tiempo agotado.</p>
        <div class="w-full bg-gray-800 rounded-full h-2.5 mb-4">
          <div class="bg-red-500 h-2.5 rounded-full" style="width: 100%"></div>
        </div>
        <p class="text-orange-400 font-medium">Ejercicios completados: ${currentEjercicioIndex} de ${totalEjercicios}</p>
      </div>
    `, {
      borderColor: 'border-red-500/30',
      autoClose: true,
      closeDelay: 3500,
      onClose: () => {
        window.location.href = '/';
      }
    });
  };

  // Función para mostrar popup de finalización
  const showCompletionPopup = (motivo, theta = null, error = null) => {
    let statsHtml = '';
    if (theta !== null && error !== null) {
      statsHtml = `
        <div class="mt-4 w-full bg-gray-800 rounded-lg p-3 border border-orange-500/30">
          <div class="flex justify-between mb-2">
            <span class="text-gray-300">Nivel estimado:</span>
            <span class="text-orange-400 font-bold">${theta.toFixed(2)}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-gray-300">Precisión:</span>
            <span class="text-green-400 font-bold">${error.toFixed(2)}</span>
          </div>
        </div>
      `;
    }

    showPopup(`
      <div class="flex flex-col items-center text-center">
        <div class="relative mb-6">
          <div class="w-16 h-16 border-4 border-green-500 rounded-full flex items-center justify-center">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
            </svg>
          </div>
        </div>
        <h3 class="text-2xl font-bold text-green-400 mb-2">¡Diagnóstico completado!</h3>
        <p class="text-gray-300 text-lg mb-1">${motivo}</p>
        <p class="text-orange-300 font-medium mb-4">Has completado ${currentEjercicioIndex - 1} ejercicios</p>
        ${statsHtml}
        <p class="text-gray-400 mt-3 text-sm">Serás redirigido en unos segundos...</p>
      </div>
    `, {
      borderColor: 'border-green-500/30',
      showCloseButton: true,
      autoClose: true,
      closeDelay: 4000,
      onClose: () => {
        window.location.href = '/';
      }
    });
  };

  // Función para mostrar popup de error
  const showErrorPopup = (message) => {
    showPopup(`
      <div class="flex flex-col items-center text-center">
        <div class="relative mb-6">
          <div class="w-16 h-16 border-4 border-red-500 rounded-full flex items-center justify-center">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
        </div>
        <h3 class="text-2xl font-bold text-red-400 mb-2">Error al procesar</h3>
        <p class="text-gray-300 text-lg mb-4">${message}</p>
        <button id="retry-btn" class="px-6 py-2 bg-orange-600 text-white rounded-lg font-medium hover:bg-orange-500 transition">
          Reintentar
        </button>
      </div>
    `, {
      borderColor: 'border-red-500/30',
      showCloseButton: true,
      backdropClose: false
    });

    // Añadir evento al botón de reintentar
    setTimeout(() => {
      const retryBtn = document.getElementById('retry-btn');
      if (retryBtn) {
        retryBtn.addEventListener('click', () => {
          sendingPopup.classList.add('hidden');
          document.body.style.overflow = 'auto';
          // Reintentar el envío
          enviarRespuesta();
        });
      }
    }, 100);
  };

  // Normalizar estilo de inputs
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
      
      // Efecto visual al mostrar/ocultar pista
      if (!hintText.classList.contains('hidden')) {
        hintText.style.opacity = '0';
        hintText.style.transform = 'translateY(10px)';
        setTimeout(() => {
          hintText.style.transition = 'all 0.3s ease-out';
          hintText.style.opacity = '1';
          hintText.style.transform = 'translateY(0)';
        }, 10);
      }
    });
  }

  // Habilitar botones de pasos
  bindStepButtons({addBtn: addStepBtn, removeBtn: removeStepBtn, stepsContainer});

  // Agregar efecto de desplazamiento suave al cambiar de ejercicio
  const smoothTransition = (element, startValue, endValue, duration = 300) => {
    let start = null;
    const animate = (timestamp) => {
      if (!start) start = timestamp;
      const elapsed = timestamp - start;
      const progress = Math.min(elapsed / duration, 1);
      
      // Easing function para transición suave
      const ease = (t) => t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;
      
      element.style.opacity = startValue + (endValue - startValue) * ease(progress);
      
      if (progress < 1) {
        requestAnimationFrame(animate);
      }
    };
    
    requestAnimationFrame(animate);
  };

  // Actualizar el temporizador
  function startTimerFromRemaining(remainingSeconds) {
    if (timer) timer.stop();
    timer = new CountdownTimer({
      remainingSeconds: remainingSeconds,
      onTick: (remaining) => {
        updateTimeDisplay(timeElement, remaining);
        // Cambiar color según tiempo restante
        if (remaining < 60) {
          timeElement.closest('div').className = 'flex items-center space-x-2 text-lg font-extrabold text-red-400';
        } else if (remaining < 180) {
          timeElement.closest('div').className = 'flex items-center space-x-2 text-lg font-extrabold text-yellow-400';
        }
      },
      onFinish: () => handleTimeUp()
    });
    timer.start();
  }

  function handleTimeUp() {
    showTimeUpPopup();
  }

  async function enviarRespuesta() {
    if (isProcessing) return;
    isProcessing = true;
    
    finalizeBtn.disabled = true;
    finalizeBtn.classList.add('opacity-75', 'cursor-wait');
    
    // Mostrar popup de envío con progreso inicial
    showLoadingPopup('Analizando tu respuesta', '??%');
    
    try {
      const ejercicioId = ejercicioIdInput.value;
      const pasos = Array.from(stepsContainer.getElementsByClassName('step-input'))
                        .map(el => el.value.trim())
                        .filter(v => v);
                        
      if (pasos.length === 0) {
        throw new Error('Completa al menos un paso.');
      }
      
      // Actualizar progreso en el popup
      const popupContent = sendingPopup.querySelector('div.bg-gray-900');
      if (popupContent) {
        popupContent.innerHTML = popupContent.innerHTML.replace('25', '50');
      }
      
      const remaining = timer ? timer.getRemainingSeconds() : 0;

      const payload = {
        ejercicio_id: parseInt(ejercicioId, 10),
        respuesta_estudiante: pasos[pasos.length - 1],
        tiempo_en_segundos: remaining,
        remaining_seconds: remaining,
        pasos: pasos
      };

      // Simular retraso para mejor experiencia de usuario
      await new Promise(resolve => setTimeout(resolve, 300));
      
      const data = await submitAnswer(payload, postUrl);
      
      if (data.success && !data.final) {
        // Simular procesamiento
        setTimeout(() => {
          // Actualizar progreso
          const popupContent = sendingPopup.querySelector('div.bg-gray-900');
          if (popupContent) {
            popupContent.innerHTML = popupContent.innerHTML.replace('50', '75');
          }
          
          // Efecto de transición en el enunciado
          const currentEnunciado = enunciadoElement.innerHTML;
          
          // Animación de salida
          smoothTransition(enunciadoElement, 1, 0, 200);
          
          setTimeout(() => {
            // Actualizar contenido
            if (data.contexto?.display_text) {
              enunciadoElement.innerHTML = data.contexto.display_text;
              
              const hintP = document.querySelector('.hint-text p');
              if (hintP) hintP.textContent = data.contexto.hint || '';
              
              if (data.ejercicio?.id) {
                ejercicioIdInput.value = data.ejercicio.id;
              }
            }
            
            // Resetear pasos
            resetStepsContainer(stepsContainer);
            
            // Actualizar contador de ejercicio
            currentEjercicioIndex++;
            updateProgressBar(currentEjercicioIndex, totalEjercicios);
            
            // Actualizar título
            headerTitle.textContent = `Ejercicio #${currentEjercicioIndex} de ${totalEjercicios}`;
            
            // Animación de entrada
            enunciadoElement.style.opacity = '0';
            enunciadoElement.style.transform = 'translateY(10px)';
            setTimeout(() => {
              enunciadoElement.style.transition = 'all 0.4s ease-out';
              enunciadoElement.style.opacity = '1';
              enunciadoElement.style.transform = 'translateY(0)';
              
              // Cerrar popup después de la animación
              setTimeout(() => {
                hideSendingPopup();
                isProcessing = false;
                finalizeBtn.disabled = false;
                finalizeBtn.classList.remove('opacity-75', 'cursor-wait');
              }, 300);
            }, 50);
          }, 200);
        }, 400);
      } else {
        // Finalizar diagnóstico
        showCompletionPopup(
          data.motivo || 'Diagnóstico finalizado.',
          data.theta,
          data.error
        );
      }
    } catch (e) {
      console.error('submitAnswer error', e);
      const errorMessage = e.message || 'No se pudo enviar la respuesta. Por favor, intenta nuevamente.';
      showErrorPopup(errorMessage);
      isProcessing = false;
    } finally {
      if (!sendingPopup.classList.contains('hidden')) {
        finalizeBtn.disabled = false;
        finalizeBtn.classList.remove('opacity-75', 'cursor-wait');
      }
    }
  }

  function hideSendingPopup() {
    if (sendingPopup) {
      const popupContent = sendingPopup.querySelector('div.bg-gray-900');
      if (popupContent) {
        // Animación de salida
        popupContent.style.transition = 'all 0.2s ease-in';
        popupContent.style.opacity = '0';
        popupContent.style.transform = 'scale(0.95)';
      }
      
      setTimeout(() => {
        sendingPopup.classList.add('hidden');
        document.body.style.overflow = 'auto';
      }, 200);
    }
  }

  finalizeBtn.addEventListener('click', enviarRespuesta);

  // Scroll automático al último input
  if (addStepBtn) {
    addStepBtn.addEventListener('click', () => {
      setTimeout(() => {
        const container = document.querySelector('.inputs');
        if (container) {
          container.scrollTo({
            top: container.scrollHeight,
            behavior: 'smooth'
          });
        }
      }, 100);
    });
  }

  // Navegación con teclado mejorada
  document.addEventListener('keydown', (e) => {
    if (isProcessing) return;
    
    if (e.key === 'Enter' && document.activeElement.classList.contains('step-input')) {
      e.preventDefault();
      const inputs = document.querySelectorAll('.step-input');
      const currentIndex = Array.from(inputs).indexOf(document.activeElement);
      
      if (currentIndex === inputs.length - 1) {
        // Si está en el último input, enfocar el botón de siguiente
        setTimeout(() => {
          finalizeBtn.focus();
        }, 100);
      } else {
        // Si no es el último, enfocar el siguiente
        inputs[currentIndex + 1].focus();
      }
    }
    
    // Atajo para enviar con Ctrl + Enter o Cmd + Enter
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      if (!isProcessing) {
        enviarRespuesta();
      }
    }
  });

  // Efecto de enfoque en el campo de texto actual
  document.addEventListener('focusin', (e) => {
    if (e.target.classList.contains('step-input')) {
      e.target.parentElement?.classList.add('ring-2', 'ring-orange-500/50');
    }
  });

  document.addEventListener('focusout', (e) => {
    if (e.target.classList.contains('step-input')) {
      e.target.parentElement?.classList.remove('ring-2', 'ring-orange-500/50');
    }
  });

  // Inicializar barra de progreso
  updateProgressBar(currentEjercicioIndex, totalEjercicios);
  
  // Iniciar el temporizador
  startTimerFromRemaining(remainingFromServer);
  
  // Inicializar con efecto de aparición suave
  setTimeout(() => {
    const mainContainer = document.querySelector('#diagnostico-root');
    if (mainContainer) {
      mainContainer.style.opacity = '0';
      mainContainer.style.transform = 'translateY(20px)';
      mainContainer.style.transition = 'all 0.5s ease-out';
      
      setTimeout(() => {
        mainContainer.style.opacity = '1';
        mainContainer.style.transform = 'translateY(0)';
      }, 100);
    }
  }, 100);
});