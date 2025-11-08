import unicodedata
from unidecode import unidecode

def normalize_text(text, for_storage=True, for_json=False):
    """
    Normaliza texto manteniendo caracteres legítimos.
    
    Args:
        text: Texto a normalizar
        for_storage: Si es para almacenar en DB (mantiene acentos)
        for_json: Si es para serializar JSON (maneja escapes)
    """
    if not text:
        return text
        
    # Paso 1: Normalización Unicode básica
    text = unicodedata.normalize('NFKC', str(text))
    
    # Paso 2: Manejo específico según uso
    if for_json:
        # Solo escapar caracteres problemáticos para JSON, no eliminar
        return text.replace('\\', '\\\\').replace('"', '\\"')
    elif not for_storage:
        # Para búsqueda o comparación: quitar acentos pero mantener legibilidad
        return unidecode(text)
    
    # Para almacenamiento: mantener caracteres legítimos intactos
    return text.strip()