# forms.py
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from .models import Disciplina, ActividadDeportiva, Estudiante, Perfil

class UserForm(forms.ModelForm):
    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Ingresa una contraseña"})
    )
    password2 = forms.CharField(  # <--- NUEVO
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
            pass  # si el user no tiene perfil, permitimos login
        

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
        # Si envían disciplina por GET, filtra actividades por esa disciplina
        data = self.data or self.initial
        disc_id = data.get("disciplina")
        if disc_id:
            self.fields["actividad"].queryset = (
                ActividadDeportiva.objects
                .filter(disciplina_id=disc_id)
                .order_by("-fecha_inicio")
            )
        else:
            # Sin disciplina, muestra todas (o deja vacío si prefieres)
            self.fields["actividad"].queryset = (
                ActividadDeportiva.objects.all().order_by("-fecha_inicio")
            )

class MarcarAsistenciaForm(forms.Form):
    perfil_id = forms.IntegerField(widget=forms.HiddenInput())
    alumno = forms.CharField(
        label="Alumno",
        required=False,  # <-- añadir
        widget=forms.TextInput(attrs={"class": "form-control", "readonly": "readonly"})
    )
    presente = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"})
    )