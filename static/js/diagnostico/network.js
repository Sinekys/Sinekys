
/**
 * Obtiene el valor de una cookie por nombre.
 * @param {string} name - Nombre de la cookie.
 * @returns {string|null} Valor de la cookie o null.
 */
function getCookie(name) {
  const cookies = document.cookie ? document.cookie.split(';') : [];
  for (let i = 0; i < cookies.length; i++) {
    const c = cookies[i].trim();
    if (c.startsWith(name + '=')) {
      return decodeURIComponent(c.substring(name.length + 1));
    }
  }
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

/**
 * Envía la respuesta del estudiante al servidor.
 * @param {Object} payload - Datos de la respuesta.
 * @returns {Promise<Object>} Respuesta del servidor.
 */
export async function submitAnswer(payload, postUrl) {
  if (!postUrl) {
    throw new Error('postUrl is required');
  }
  const csrftoken = getCookie('csrftoken');
  const response = await fetch(postUrl, {
    method: 'POST',
    credentials: 'same-origin',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrftoken,
      'X-Requested-With': 'XMLHttpRequest'
    },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    const text = await response.text().catch(() => null);
    const err = new Error(`HTTP error! status: ${response.status}`);
    err.status = response.status;
    err.statusText = response.statusText;
    err.responseText = text;
    throw err;
  }
  return response.json();
}
