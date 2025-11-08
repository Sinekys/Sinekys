import os, json, time,re,logging
import unicodedata
from openai import OpenAI
from dotenv import load_dotenv
from ..utils.text import normalize_text


load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = os.getenv("MODEL", "gpt-4o-mini") 
logger = logging.getLogger(__name__)

def _extract_json_like(text:str) -> str | None:
    # estrategia 1: Buscar entre llaves
    start = text.find("{")
    end = text.rfind("}") + 1
    if start != -1 and end != -1 and end > start:
        candidate = text[start:end]
        return candidate
    # Estrategia 2: Buscar regex
    m = re.search(r'(\{.*\})', text, re.DOTALL)
    if m:
        return m.group(1)
    
    # Estrategia 3: Buscar bloques de texto que parezcan JSON
    m = re.search(r'(\{(?:[^{}]|(?R))*\})', text, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1)
    return None


def _sanitize_json_string(json_str: str) -> str:
    if not isinstance(json_str, str):
        return json_str
    normalized = unicodedata.normalize('NFKC', json_str)
    return normalized.replace('\\', '\\\\').replace('"', '\\"')
# Función para ejercicio estándar y grupos
def build_prompt(payload, carrera):
    system = (
        f'Eres un profesor universitario de {carrera}. Responde en español. '
        "Cuando te pidan contextualizar un enunciado, genera un JSON válido con "
        "display_text, exercise, learning_objective, tags, hint (opcional)." #Revisar si estos atributos de respuestas son realmente necesario y/o se ajustan a la DB
    )
    user = json.dumps(payload, ensure_ascii=False)
    return system, user

def safe_create_response(payload, carrera, max_retries=2):
    system, user = build_prompt(payload, carrera)
    attempt = 0
    while True:
        try:
            resp = client.responses.create(
                model=MODEL,
                instructions=system,
                input=user,
                temperature=0.2,
                max_output_tokens=256
            )
            text = resp.output_text.strip()
            try: 
                return json.loads(text)
            except json.JSONDecodeError:
                json_candidate = _extract_json_like(text)
                if not json_candidate:
                    logger.warning("No se pudo extraer JSON de la respuesta del LLM, LLM output: %s", text[:1000])
                    raise
                try:
                    return json.loads(_sanitize_json_string(json_candidate))
                except json.JSONDecodeError as e2:
                    logger.exception("safe_create_response: fallo parseo JSON. intent1 error=%s intent2 error=%s\nLLM raw (trunc): %s", e, e2, text[:2000])
                    raise
        except Exception as exc:
            attempt += 1
            if attempt > max_retries:
                # ultimo recurso, fallback seguro para no romper la app
                logger.exception("safe_create_response: max_retries alcanzado. payload=%s, carrera=%s, last_exc=%s", payload, carrera, exc)
                return {
                "display_text": payload.get("EJERCICIO", getattr(payload, "EJERCICIO", "Ejercicio")),
                "exercise": payload.get("EJERCICIO", ""),
                "learning_objective": "Contexto no disponible",
                "tags": ["fallback"],
                "hint": "No se pudo generar contexto automático en este momento."
                }
            time.sleep(1 + attempt*0.5)
            continue

def contextualize_exercise(ejercicio, carrera):
    try:
        # Normalizar para almacenamiento (mantener acentos)
        carrera_str = normalize_text(carrera, for_storage=True)
        ejercicio_str = normalize_text(ejercicio.enunciado, for_storage=True)
        
        payload = {
            "CARRERA": carrera_str,
            "EJERCICIO": ejercicio_str,
            "NIVEL": "intermedio",
            "USO_EN_SISTEMA": "Sinekys: modo adaptivo"
        }
        
        # Normalizar para JSON al enviar al LLM
        return safe_create_response(
            payload, 
            normalize_text(carrera_str, for_json=True)
        )
    except Exception as e:
        logger.exception("Error en contextualize_exercise: %s", str(e))
        return {
            "display_text": normalize_text(ejercicio.enunciado, for_storage=True),
            "hint": f"Contexto para {normalize_text(carrera, for_storage=True)} no disponible temporalmente"
        }