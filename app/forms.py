import bcrypt
from django import forms
from app.models import *
from .models import Usuario, ActividadDeportiva, Asistencia, Estudiante, Disciplina
from django.forms import formset_factory    

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


class UsuarioEditForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ['nombre_usuario','rol']
        widgets = {
            'nombre_usuario': forms.TextInput(attrs={'class': 'form-control'}),
            'rol': forms.Select(attrs={'class': 'form-select'}),
        }

class SeleccionarActividadForm(forms.Form):
    disciplina = forms.ModelChoiceField(
        queryset=Disciplina.objects.all().order_by('nombre'),
        required=True,
        label="Disciplina",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    actividad = forms.ModelChoiceField(
        queryset=ActividadDeportiva.objects.none(),
        required=True,
        label="Actividad deportiva",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        d = None
        if self.data.get('disciplina'):
            d = self.data.get('disciplina')
        elif self.initial.get('disciplina'):
            d = self.initial.get('disciplina')

        if d:
            self.fields['actividad'].queryset = ActividadDeportiva.objects.filter(disciplina_id=d).order_by('-fecha_inicio')
        else:
            self.fields['actividad'].queryset = ActividadDeportiva.objects.all().order_by('-fecha_inicio')


ESTADOS = Asistencia.ESTADOS

class AsistenciaItemForm(forms.Form):
    estudiante_id = forms.IntegerField(widget=forms.HiddenInput())
    alumno = forms.CharField(disabled=True, required=False, widget=forms.TextInput(attrs={'class': 'form-control-plaintext fw-semibold'}))
    estado = forms.ChoiceField(
        choices=ESTADOS,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        required=True,
        label=""
    )

AsistenciaFormSet = formset_factory(AsistenciaItemForm, extra=0, min_num=1, validate_min=True)

