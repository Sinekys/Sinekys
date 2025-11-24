# Aqui ira toda la lógica relacionada con 
# Darle feedback al usuario sobre sus respuestas
import requests
from django.conf import settings
from ejercicios.models import Ejercicio, PasoEjercicio, Intento,IntentoPaso,Feedback, FeedbackPasos #no sé si vaya a usar este ultimo la verdad
from accounts.models import Estudiante
from django.utils import timezone
import os,json,time,logging,re,unicodedata

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("SINEKYS_OPENAI_API_KEY"))
MODEL = os.getenv("MODEL", "gpt-4o-mini") 
logger = logging.getLogger(__name__)

def _extract_json_like(text: str) -> str | None:
    start = text.find("{")
    end = text.rfind("}") + 1
    if start != -1 and end != -1 and end > start:
        return text[start:end]
    m = re.search(r'(\{(?:[^{}]|(?R))*\})', text, re.DOTALL)
    if m:
        return m.group(0)
    return None

def _sanitize_json_string(json_str: str) -> str:
    if not isinstance(json_str, str):
        return json_str
    json_str = unicodedata.normalize('NFKC', json_str)
    # evitar romper JSON con comillas sin escapar
    json_str = json_str.replace('\\', '\\\\').replace('“', '"').replace('”', '"').replace("'", '"')
    # eliminar control chars
    json_str = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', json_str).strip()
    return json_str

def call_my_ai_service(payload: dict, max_retries: int = 2, temperature: float = 0.3) -> dict:
    #Retorna: {"texto": str, "feedback_json": dict, "pasos": list}
    
    enunciado = payload.get("enunciado", "")
    respuesta_est = payload.get("respuesta_estudiante", "")
    solucion = payload.get("solucion", "")
    carrera = payload.get("carrera ", "")
    pasos = payload.get("pasos", [])
    
    system = (
        "Eres un profesor universitario experto en matemáticas. "
        "Genera una explicación pedagógica y una corrección paso a paso para el estudiante. "
        "RESPONDE UN SOLO JSON VÁLIDO (NADA MÁS) con al menos estas claves:\n"
        " - 'texto': explicación completa (puede ser larga)\n"
        " - 'feedback_json': objeto con estructura de corrección (ej: pasos, errores comunes)\n"
        " - 'pasos': (opcional) lista de pasos con 'tipo' y 'contenido'\n\n"
        "No incluyas texto fuera del JSON. Si no puedes, intenta devolver un JSON parcial que se pueda parsear."
    )
    user = (
        f'{{"enunciado": {json.dumps(enunciado, ensure_ascii=False)}, '
        f'"respuesta_estudiante": {json.dumps(respuesta_est, ensure_ascii=False)}, '
        f'"solucion": {json.dumps(solucion, ensure_ascii=False)}, '
        f'"carrera": {json.dumps(carrera, ensure_ascii=False)}, '
        f'"pasos": {json.dumps(pasos, ensure_ascii=False)} }}'
    )
    attempt = 0
    while attempt < max_retries:
        attempt += 1
        try:
            logger.debug("LLM feedback call attempt %d for enunciado[:80]=%s", attempt, enunciado[:80])
            resp = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user}
                ],
                temperature=temperature,
                max_tokens=1500,
                response_format={"type": "text"}  # texto libre para parsear
            )
            text = resp.choices[0].message.content.strip()
            logger.debug("LLM feedback raw response: %s", text[:800])
            
          # intentar parsear JSON
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                candidate = _extract_json_like(text)
                if candidate:
                    try:
                        sanitized = _sanitize_json_string(candidate)
                        parsed = json.loads(sanitized)
                    except Exception as e2:
                        logger.warning("parse after sanitize failed: %s", str(e2))
                        parsed = None
                else:
                    parsed = None
            if isinstance(parsed, dict):
                texto = parsed.get("texto") or parsed.get("contexto") or parsed.get("explanacion") or ""
                feedback_json = parsed.get("feedback_json") or parsed.get("correccion") or parsed.get("feedback") or {}
                pasos_res = parsed.get("pasos") or []
                return {"texto": texto, "feedback_json": feedback_json, "pasos": pasos_res}
            else:
                logger.warning("LLM returned no JSON-parsable content; attempt %d", attempt)
                if attempt < max_retries:
                    time.sleep(0.8 * attempt)
                    continue
                # fallback: devolver un texto simple con el enunciado + pista
                return {
                    "texto": f"Explicación automática (fallback). Repasa el enunciado: {enunciado}",
                    "feedback_json": {},
                    "pasos": []
                }

        except Exception as exc:
            logger.exception("Error calling LLM (attempt %d): %s", attempt, str(exc))
            if attempt < max_retries:
                time.sleep(1.0 * attempt)
                continue
            return {
                "texto": f"Servicio de IA temporalmente no disponible. Intenta de nuevo.",
                "feedback_json": {},
                "pasos": []
            }
