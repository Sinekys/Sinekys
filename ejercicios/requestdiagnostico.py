import os, json, time
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = os.getenv("MODEL", "gpt-4o-mini") 


def build_prompt_diagnostico(payload):
    system = (
        "Eres un profesor de matemáticas de nivel introductorio. "
        "Responde en español con un lenguaje claro, sencillo y general. "
        "Cuando te pidan contextualizar un enunciado para una prueba diagnóstica, "
        "genera un JSON válido con las siguientes claves: "
        "display_text, exercise, learning_objective, tags, hint (opcional). "
        "No incluyas referencias a carreras o especialidades, ni ejemplos contextualizadores, nada de eso."
    )
    user = json.dumps(payload, ensure_ascii=False)
    return system, user


def safe_create_response_diagnostico(payload, max_retries=2):
    system, user = build_prompt_diagnostico(payload)
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
            start = text.find("{")
            end = text.rfind("}") + 1
            json_text = text[start:end]
            parsed = json.loads(json_text)
            return parsed
        except Exception:
            attempt += 1
            if attempt > max_retries:
                raise
            time.sleep(1 + attempt*0.5)

def contextualize_exercise_diagnostico(ejercicio):
    """
    Versión neutra: genera un contexto simple para pruebas diagnósticas.
    """
    try:
        payload = {
        "EJERCICIO": ejercicio.enunciado,
        "TIPO": "diagnostico",
        "NIVEL": "basico",
        "USO_EN_SISTEMA": "Prueba diagnóstica inicial",
        }
        return safe_create_response_diagnostico(payload)
    except Exception:
        # fallback seguro
        return {
            "display_text": ejercicio.enunciado,
            "hint":"Piensa el ejercicio en partes lo más pequeñas posibles",
            "exercise": ejercicio.enunciado,
            "learning_objective": "Evaluar conocimientos básicos",
            "tags": ["diagnostico"]
        }
