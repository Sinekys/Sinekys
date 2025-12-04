# ejercicios/converters.py
import re
import uuid
from django.core.exceptions import ValidationError

class UUIDConverter:
    regex = '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
    
    def to_python(self, value):
        try:
            return uuid.UUID(value)
        except ValueError:
            raise ValidationError('UUID inválido')
    
    def to_url(self, value):
        return str(value)