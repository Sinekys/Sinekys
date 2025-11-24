import os, json, time,re,logging
import unicodedata
from openai import OpenAI
from dotenv import load_dotenv
from ..utils.text import normalize_text


load_dotenv()
client = OpenAI(api_key=os.getenv("SINEKYS_OPENAI_API_KEY"))
MODEL = os.getenv("MODEL", "gpt-4o-mini") 
logger = logging.getLogger(__name__)

#extraer contenido json de texto con múltiples estrategias robustas
def _extract_json_like(text:str) -> str | None:
    # estrategia 1: Buscar entre llaves
    start = text.find("{")
    end = text.rfind("}") + 1
    if start != -1 and end != -1 and end > start:
        return text[start:end]
    # Regex para json válido
    m = re.search(r'\{(?:[^{}]|(?R))*\}', text, re.DOTALL)
    if m:
        return m.group(0)
    # Estrategia 2: Buscar regex
    m = re.search(r'(\{.*\})', text, re.DOTALL)
    if m:
        return m.group(1)
    
    # Estrategia 3: Buscar bloques de texto que parezcan JSON
    m = re.search(r'(\{(?:[^{}]|(?R))*\})', text, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1)
    return None

# sanitiza y mantiene caracteres utf8 válidos
def _sanitize_json_string(json_str: str) -> str:
    if not isinstance(json_str, str):
        return json_str
    # Normalizar Unicode manteniendo caracteres legítimos
    json_str = unicodedata.normalize('NFKC', json_str)
    # Escapar solo caracteres problemáticos para JSON
    json_str = json_str.replace('\\', '\\\\').replace('"', '\\"')
    # Eliminar caracteres de control excepto espacios
    return re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', json_str).strip()
# Función para ejercicio estándar y grupos
def build_prompt(carrera, ejercicio_enunciado):
    # ejemplos_contexto = {
        # Traer aquí ejemplos reales usando fine-tuning o RAG 
    # }
    system = (     
        f"""
            Eres un profesor universitario *experto* en {carrera}. Tu tarea es convertir ejercicios matemáticos en *contextos reales de aplicación profesional* para estudiantes de esa carrera.

            INSTRUCCIONES:
            1. No proporciones la solución al ejercicio.
            2. No expliques cómo resolverlo.
            3. Genera únicamente un JSON válido con los siguientes campos:
            - "display_text": Enunciado del ejercicio, reformulado para que el estudiante visualice **una situación concreta en {carrera}** donde debe aplicar lo aprendido.
            - "hint": Una pista **específica al contexto profesional de {carrera}**, máximo 2 oraciones.

            REQUISITOS:
            - El contexto debe describir un escenario plausible en esa carrera donde el ejercicio importa.
            - El lenguaje debe ser del nivel “estudiante universitario de la carrera” (no de escuela secundaria) y motivador (“en tu futura práctica profesional…”).
            - El JSON debe tener exactamente esos campos, sin texto adicional, comentarios, explicaciones.

            """

            # EJEMPLO DE SALIDA VÁLIDA:
            # {{"display_text": "{ejemplos['ejercicio']}", "hint": "{ejemplos['contexto']}"}}
        #"display_text, exercise, learning_objective, tags, hint (opcional)." #Revisar si estos atributos de respuestas son realmente necesario y/o se ajustan a la DB
    )
    user = f"""
        Contextualiza este ejercicio para estudiantes de {carrera}:
        Ejercicio: {ejercicio_enunciado}
        """
    logger.debug("Prompt system: %s", system.strip())
    logger.debug("Prompt user: %s", user.strip())
    
    return system.strip(), user.strip()

def safe_create_response(payload, carrera, max_retries=2):
    ejercicio_enunciado = payload.get("EJERCICIO", "")
    carrera_sanitizada = normalize_text(carrera, for_storage=True)
    # ejercicio_sanitizado = normalize_text(ejercicio_enunciado, for_storage=True)
    system, user = build_prompt(carrera, ejercicio_enunciado)
    attempt = 0
    while attempt < max_retries:
        try:
            attempt += 1
            logger.debug("LLM Request attempt %d for carrera=%s, ejercicio_id=%s", attempt, carrera_sanitizada, getattr(payload, "ejercicio_id", "?"))
            
            resp = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user}
                ],
                temperature=0.3,
                max_tokens=512,
                # max_output_tokens=256,
                response_format={"type": "json_object"} #forzar que el formato json es el válido
            )
            # obtener contenido
            text = resp.choices[0].message.content.strip()
            logger.debug("LLM Response received for carrera=%s, ejercicio_id=%s: %s", carrera_sanitizada, getattr(payload, "ejercicio_id", "?"), text[:1000])
            try: 
                parsed = json.loads(text)
                logger.debug("safe_create_response: JSON parsed successfully on attempt %d for carrera=%s, ejercicio_id=%s", attempt, carrera_sanitizada, getattr(payload, "ejercicio_id", "?"))
                if "display_text" in parsed:
                    parsed["display_text"] = normalize_text(parsed["display_text"], for_storage=True)
                    return parsed
                logger.warning("safe_create_response: 'display_text' missing in parsed JSON on attempt %d for carrera=%s, ejercicio_id=%s", attempt, carrera_sanitizada, getattr(payload, "ejercicio_id", "?"))
            except json.JSONDecodeError as e:
                logger.warning("safe_create_response: fallo parseo JSON en attempt %d for carrera=%s, ejercicio_id=%s, error=%s", attempt, carrera_sanitizada, getattr(payload, "ejercicio_id", "?"), str(e))
                json_candidate = _extract_json_like(text)
                if json_candidate:
                    try:
                        sanitized = _sanitize_json_string(json_candidate)
                        parsed = json.loads(sanitized)
                        if "display_text" in parsed:
                            logger.debug("safe_create_response: JSON parsed successfully after sanitization on attempt %d for carrera=%s, ejercicio_id=%s", attempt, carrera_sanitizada, getattr(payload, "ejercicio_id", "?"))
                            return parsed
                        logger.warning("safe_create_response: 'display_text' missing in sanitized JSON on attempt %)d for carrera=%s, ejercicio_id=%s", attempt, carrera_sanitizada, getattr(payload, "ejercicio_id", "?"))
                    except json.JSONDecodeError as e2:
                        logger.warning("safe_create_response: fallo parseo JSON sanitizado en attempt %d for carrera=%s, ejercicio_id=%s, error=%s", attempt, carrera_sanitizada, getattr(payload, "ejercicio_id", "?"), str(e2))
                        logger.debug("JSON candidate: %s", json_candidate)
            if attempt < max_retries:
                time.sleep(attempt * 0.7)
        except Exception as exc:
            logger.error("Error en intento %d: %s", attempt, str(exc))
            logger.exception("Detalles de la excepción:")
            
            if attempt >= max_retries:
                logger.exception("safe_create_response: max_retries alcanzado. carrera=%s", carrera_sanitizada)
                break
            time.sleep(attempt * 1.0)
    return {
        "display_text": ejercicio_enunciado,
        "hint": f"Contexto académico para {carrera_sanitizada}: este tipo de ejercicio es relevante en tu formación profesional."
    }

def contextualize_exercise(ejercicio, carrera):
    try:
        carrera_str = normalize_text(carrera, for_storage=True)
        ejercicio_str = normalize_text(ejercicio.enunciado, for_storage=True)
        
        payload = {
            "CARRERA": carrera_str,
            "EJERCICIO": ejercicio_str,
            "NIVEL": "intermedio",
            "USO_EN_SISTEMA": "Sinekys: modo adaptivo"
        }
        logger.debug("Contextualizing exercise for carrera=%s, ejercicio_id=%s", carrera_str, ejercicio.id)
        result = safe_create_response(
            payload, 
            carrera_str
        )
        if "display_text" not in result:
            result["display_text"]=ejercicio_str
        if "hint" not in result:
            result["hint"]= f'Pista contextualizada para {carrera_str}.'
        logger.info("Contextualization successful for carrera=%s, ejercicio_id=%s", carrera_str, ejercicio.id)
        return result

    except Exception as e:
        logger.exception("Error en contextualize_exercise: %s", str(e))
        return {
            "display_text": normalize_text(ejercicio.enunciado, for_storage=True),
            "hint": f"Contexto para {normalize_text(carrera, for_storage=True)} no disponible temporalmente"
        }
         
# Ok, hasta el momento tengo 2 errores, el primero es que siempre me da el mismo ejercicio | Error solucionado Error solucionado Error solucionado Error solucionado
# El segundo es que no me da un contexto apropiado | Pendiente

# librería