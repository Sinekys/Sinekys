document.addEventListener("DOMContentLoaded", function() {
  const stepsContainer = document.getElementById("steps-container");
  const addStepBtn = document.getElementById("add-step-btn");
  const removeStepBtn = document.getElementById("remove-step-btn");
  const finalizeBtn = document.getElementById("finalize-btn");
  const timeElement = document.querySelector(".time");
  
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

  // 3. Finalizar ejercicio - ¡Este código debe estar dentro de un evento de clic!
  finalizeBtn.addEventListener("click", function() {
    const steps = [];
    const inputs = stepsContainer.getElementsByClassName("step-input");
    
    // Recoger todos los pasos completados
    for (let i = 0; i < inputs.length; i++) {
      if (inputs[i].value.trim() !== '') {
        steps.push({
          orden: i + 1,
          contenido: inputs[i].value.trim()
        });
      }
    }
    
    // Validar que haya al menos un paso
    if (steps.length === 0) {
      alert("Por favor, completa al menos un paso antes de terminar.");
      return;
    }
    
    // Aquí procesarías los pasos (ej: enviar al servidor)
    console.log("Pasos completados:", steps);

});
});