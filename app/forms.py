# forms.py
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from app.models import *

class UserForm(forms.ModelForm):
    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Ingresa una contraseña"})
    )
    password2 = forms.CharField(
        label="Repite la contraseña",
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Repite la contraseña"})
    )

    class Meta:
        model = User
        fields = ["username", "email", "password", "password2", "first_name", "last_name"]
        widgets = {
            "username":   forms.TextInput(attrs={"class": "form-control", "placeholder": "Nombre de usuario"}),
            "email":      forms.EmailInput(attrs={"class": "form-control", "placeholder": "correo@dominio.com"}),
            "first_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nombre(s)"}),
            "last_name":  forms.TextInput(attrs={"class": "form-control", "placeholder": "Apellidos"}),
        }

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password")
        p2 = cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Las contraseñas no coinciden.")
        return cleaned

class PerfilForm(forms.ModelForm):
    class Meta:
        model = Perfil
        fields = ["run", "telefono", "direccion", "rol"]
        widgets = {
            "run":       forms.TextInput(attrs={"class": "form-control", "placeholder": "RUN/DNI"}),
            "telefono":  forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej: +56 9 1234 5678"}),
            "direccion": forms.TextInput(attrs={"class": "form-control", "placeholder": "Calle, número, ciudad"}),
            "rol":       forms.Select(attrs={"class": "form-select"}),
        }

class PerfilAuthForm(AuthenticationForm):
    def confirm_login_allowed(self, user):
        try:
            perfil = user.perfil
            if not perfil.activo:
                raise forms.ValidationError(
                    "Tu cuenta está deshabilitada. Contacta a un administrador.",
                    code="inactive",
                )
        except Perfil.DoesNotExist:
            pass

class EstudianteForm(forms.ModelForm):
    class Meta:
        model = Estudiante
        fields = ["curso", "fecha_ingreso"]
        widgets = {
            "curso": forms.Select(attrs={"class": "form-select"}),
            "fecha_ingreso": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        }

class SeleccionarActividadForm(forms.Form):
    disciplina = forms.ModelChoiceField(
        queryset=Disciplina.objects.all().order_by("nombre"),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"})
    )
    actividad = forms.ModelChoiceField(
        queryset=ActividadDeportiva.objects.none(),
        required=True,
        widget=forms.Select(attrs={"class": "form-select"})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        data = self.data or self.initial
        disc_id = data.get("disciplina")
        if disc_id:
            self.fields["actividad"].queryset = (
                ActividadDeportiva.objects
                .filter(disciplina_id=disc_id)
                .order_by("-fecha_inicio")
            )
        else:
            self.fields["actividad"].queryset = (
                ActividadDeportiva.objects.all().order_by("-fecha_inicio")
            )

class MarcarAsistenciaForm(forms.Form):
    perfil_id = forms.IntegerField(widget=forms.HiddenInput())
    alumno = forms.CharField(
        label="Alumno",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "readonly": "readonly"})
    )
    presente = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"})
    )

class DisciplinaForm(forms.ModelForm):
    class Meta:
        model = Disciplina
        fields = ['nombre', 'descripcion']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['nombre'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Ej. Preparación Física'
        })
        self.fields['descripcion'].widget.attrs.update({
            'class': 'form-control',
            'rows': 4, 
            'placeholder': 'Describe la disciplina...'
        })


class ActividadDeportivaForm(forms.ModelForm):
    class Meta:
        model = ActividadDeportiva
        fields = ['nombre', 'disciplina', 'fecha_inicio', 'fecha_fin', 'lugar']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Entrenamiento de Voleibol'}),
            'disciplina': forms.Select(attrs={'class': 'form-select'}),
            'fecha_inicio': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'fecha_fin': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'lugar': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Gimnasio Principal'}),
        }

    def clean(self):
        cleaned = super().clean()
        fecha_inicio = cleaned.get('fecha_inicio')
        fecha_fin = cleaned.get('fecha_fin')
        
        if fecha_inicio and fecha_fin and fecha_fin < fecha_inicio:
            self.add_error('fecha_fin', 'La fecha de fin no puede ser anterior a la fecha de inicio.')
        
        return cleaned


class InscripcionForm(forms.ModelForm):
    class Meta:
        model = Inscripcion
        fields = ['estudiante', 'disciplina', 'estado']
        widgets = {
            'estudiante': forms.Select(attrs={'class': 'form-select'}),
            'disciplina': forms.Select(attrs={'class': 'form-select'}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrar solo estudiantes activos
        self.fields['estudiante'].queryset = (
            Estudiante.objects
            .filter(perfil__activo=True)
            .select_related('perfil__user')
            .order_by('perfil__user__last_name', 'perfil__user__first_name')
        )