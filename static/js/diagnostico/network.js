
/**
 * Envía la respuesta del estudiante al servidor.
 * @param {Object} payload - Datos de la respuesta.
 * @returns {Promise<Object>} Respuesta del servidor.
 */
export async function submitAnswer(payload) {
  const response = await fetch('/ejercicios/diagnostico/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCookie('csrftoken'),
      'X-Requested-With': 'XMLHttpRequest'
    },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}

/**
 * Obtiene el valor de una cookie por nombre.
 * @param {string} name - Nombre de la cookie.
 * @returns {string|null} Valor de la cookie o null.
 */
function getCookie(name) {
  if (typeof document === 'undefined') return null;
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}