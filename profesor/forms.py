from django import forms
from core.models import Materia

class UploadExcelForm(forms.Form):
    materia = forms.ModelChoiceField(
        queryset=Materia.objects.all(),
        empty_label="Seleccione una materia",
        widget=forms.Select(attrs={
            'class': 'w-full p-3 border border-gray-300 rounded-lg bg-gray-50 text-black focus:ring-2 focus:ring-indigo-500'
        }),
        label="Materia"
    )
    
    archivo_excel = forms.FileField(
        widget=forms.FileInput(attrs={
            'class': 'w-full p-3 border border-gray-300 rounded-lg bg-gray-50 text-black',
            'accept': '.xlsx,.xls'
        }),
        label="Archivo Excel",
        help_text="Formatos permitidos: .xlsx, .xls"
    )
    
    def clean_archivo_excel(self):
        archivo = self.cleaned_data.get('archivo_excel')
        if archivo:
            # Validar extensión
            if not archivo.name.endswith(('.xlsx', '.xls')):
                raise forms.ValidationError("Solo se permiten archivos .xlsx o .xls")
            
            # Validar tamaño (máximo 5MB)
            if archivo.size > 5 * 1024 * 1024:
                raise forms.ValidationError("El archivo no debe superar los 5MB")
        
        return archivo