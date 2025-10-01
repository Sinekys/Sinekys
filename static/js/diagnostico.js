document.addEventListener("DOMContentLoaded", function() {
  const stepsContainer = document.getElementById("steps-container");
  const addStepBtn = document.getElementById("add-step-btn");
  const removeStepBtn = document.getElementById("remove-step-btn");
  const finalizeBtn = document.getElementById("finalize-btn");
  const timeElement = document.querySelector(".time");
  const enunciadoElement = document.getElementById("enunciado")
  
let tiempo = 0;
let timer;

function iniciarTemporizador(){
  timer = setInterval(()=> {
    tiempo++;
    const minutos = Math.floor(tiempo/60).toString().padStart(2,"0");
    const segundos = (tiempo % 60).toString().padStart(2,"0");
    timeElement.textContent = `Tiempo: ${minutos}:${segundos}`;

    if (tiempo >= 59 * 60){
      clearInterval(timer)
      finalizarDiagnostico("Tiempo agotado")
    }
  }, 1000);
}

// función para finalizar diagnostico
async function  finalizarDiagnostico(mensaje) {
  // Enviar un últim POST indicando fin por tiempo | Pendiente
  alert(mensaje + 'Diagnóstico finalizado')
  window.location.href = "/inicio/"
}


  // 1. Agregar un nuevo paso
  addStepBtn.addEventListener("click", function() {
    const newInput = document.createElement("input");
    newInput.type = "text";
    newInput.name = "step[]";
    newInput.classList.add("step-input");
    newInput.placeholder = "Nuevo paso";
    newInput.autofocus = true;
    
    stepsContainer.appendChild(newInput);
  });

  // 2. Quitar el último paso (dejando al menos uno)
  removeStepBtn.addEventListener("click", function() {
    const stepInputs = stepsContainer.getElementsByClassName("step-input");
    if (stepInputs.length > 1) { // Dejar al menos un input
      stepsContainer.removeChild(stepInputs[stepInputs.length - 1]);
    }
  });


// enviar ejercicio
async function enviarRespuesta(){
  const ejercicioId = document.getElementById("ejercicio-id").value;

    const pasos = []; //pasos
    const inputs = stepsContainer.getElementsByClassName("step-input");
    
    // Recoger todos los pasos completados
    for (let i = 0; i < inputs.length; i++) {
      const valor = inputs[i].value.trim();
      if (valor){
        pasos.push(valor)
      }
    }
    if (pasos.length === 0){
      alert("Por favor, completa al menos un paso.")
      return;
    }
    const respuestaEstudiante = pasos[pasos.length -1]; //último paso como respuesta

    const payload = {
      ejercicio_id : parseInt(ejercicioId),
      respuesta_estudiante: respuestaEstudiante,
      tiempo_en_segundos: tiempo,
      pasos: pasos
    };
    try{
      const response = await fetch("/ejercicios/diagnostico",{
        method:"POST",
        headers:{
          "Content-Type": "application/json",
          "X-CSRFToken": getCookie("csrftoken"),
          "X-Requested-With": "XMLHttpRequest",
        },
        body: JSON.stringify(payload),
      });

      const data = await response.json();
      if (data.success){
        stepsContainer.innerHTML = `<input type="text" name="step[]" class="step-input" placeholder="Empieza aquí ^^" autofocus>`;
        tiempo = 0;
        clearInterval(timer);
        iniciarTemporizador();

        
        cargarSiguienteEjercicio();
      } else {
        alert("Error: " + (data.mensaje || "No se pudo procesar"))
      }
    }catch (error){
      alert("Error:" + (data.mensaje || "No se pudo procesar"));
    }

}


});


// cargar siguiente ejercicio
async function cargarSiguienteEjercicio(){
  try {
    const response = await fetch("/ejercicio/diagnostico",{
      method: "GET",
      headers: {"X-Requested-With":"XMLHttpRequest"},
    });
    const data = await response.json();

    if (data.error){
      Swal.fire("Fin del diagnóstico");
      window.location.href = "/inicio"; //redirigir
      return
    }

    // Actualizar UI
    enunciadoElement.textContent = data.contexto.display_text;
    document.querySelector(".hint-text p").textContent = data.context.hint;
    document.getElementById("ejercicio-id").value = data.ejercicio.id;
  } catch(error){
    console.log("Error cargando el ejercicio", error);
  }
}
  iniciarTemporizador();


// Reflexión: Mucho de este código debería ser reutilizable ya
// que se utilizará tanto para la prueba de diagnostico como para los ejercicios normales
// Solo que en los ejercicios normales van a tener retroalimentación