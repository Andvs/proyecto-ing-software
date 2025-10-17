import bcrypt
from django import forms
from app.models import *

class UsuarioForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ['nombre_usuario', 'contraseña', 'rol']
        widgets = {
            'nombre_usuario': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre (solo letras)',
                'minlength': '3', 'maxlength': '50'
            }),
            'contraseña': forms.PasswordInput(attrs={
                'class': 'form-control',
                'placeholder': 'Contraseña (8–20, con mayúscula y minúscula)',
                'minlength': '8', 'maxlength': '20'
            }),
            'rol': forms.Select(attrs={'class': 'form-control'})
        }
        error_messages = {
            'nombre_usuario': {
                'required': 'El nombre es obligatorio.',
                'min_length': 'El nombre debe tener al menos 3 caracteres.',
            },
            'contraseña': {
                'required': 'La contraseña es obligatoria.',
                'min_length': 'La contraseña debe tener al menos 8 caracteres.',
                'max_length': 'La contraseña no puede superar 20 caracteres.',
            },
            'rol': {
                'required': 'Debe seleccionar un rol.',
            }
        }        
    def save(self, commit=True):
        usuario = super().save(commit=False)
        password_plano = self.cleaned_data['contraseña']
        hashed = bcrypt.hashpw(password_plano.encode('utf-8'), bcrypt.gensalt())
        usuario.contraseña = hashed.decode('utf-8')
        if commit:
            usuario.save()
        return usuario