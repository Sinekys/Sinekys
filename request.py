import os, json, time
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = os.getenv("MODEL", "gpt-4o-mini") 

def build_prompt(payload, carrera):
    system = (
        f'Eres un profesor universitario de {carrera}. Responde en español. '
        "Cuando te pidan contextualizar un enunciado, genera un JSON válido con "
        "display_text, exercise, learning_objective, difficulty, tags, hint (opcional) y metadata." #Revisar si estos atributos de respuestas son realmente necesario y/o se ajustan a la DB
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
            # intentar extraer JSON: puede venir solo JSON o texto + JSON
            # buscamos la primera { ... } con un parse seguro
            start = text.find("{")
            end = text.rfind("}") + 1
            json_text = text[start:end]
            parsed = json.loads(json_text)
            return parsed
        except Exception as e:
            attempt += 1
            if attempt > max_retries:
                raise
            time.sleep(1 + attempt*0.5)

# uso
# request.py
def contextualize_exercise(ejercicio, carrera):
    payload = {
        "CARRERA": carrera,
        "EJERCICIO": ejercicio.enunciado,
        "NIVEL": "intermedio",  # you might want to compute this later
        "USO_EN_SISTEMA": "Sinekys: modo adaptivo",
        "PERSONALIZACION": {"estudiante": "test_user"}
    }
    return safe_create_response(payload, carrera)


# print(resultado["display_text"])
