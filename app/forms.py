# forms.py
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from app.models import *
import re
from datetime import date

class UserForm(forms.ModelForm):
    password = forms.CharField(
        label="Contraseña",
        required=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Ingresa una contraseña",
                "maxlength": 20,  # límite visual
            }
        ),
    )
    password2 = forms.CharField(
        label="Repite la contraseña",
        required=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Repite la contraseña",
                "maxlength": 20,  # límite visual
            }
        ),
    )

    class Meta:
        model = User
        fields = ["username", "email", "password", "password2", "first_name", "last_name"]
        widgets = {
            "username": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Nombre de usuario",
                    "maxlength": 20,   # límite visual
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "correo@dominio.com",
                    "maxlength": 150,  # límite visual
                }
            ),
            "first_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Nombre(s)",
                    "maxlength": 50,   # límite visual
                }
            ),
            "last_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Apellidos",
                    "maxlength": 50,   # límite visual
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        self.is_edit = kwargs.pop('is_edit', False)
        super().__init__(*args, **kwargs)

        if not self.is_edit:
            self.fields['password'].required = True
            self.fields['password2'].required = True

        # 🔹 Refuerzo por si se sobreescriben los widgets en otro lado
        limits = {
            "username": 20,
            "email": 150,
            "first_name": 50,
            "last_name": 50,
        }
        for nombre_campo, maxlen in limits.items():
            if nombre_campo in self.fields:
                self.fields[nombre_campo].widget.attrs["maxlength"] = maxlen

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if not username:
            raise ValidationError("El nombre de usuario es obligatorio.")
        if len(username) < 3:
            raise ValidationError("El nombre de usuario debe tener al menos 3 caracteres.")
        # 🔹 límite real en backend
        if len(username) > 20:
            raise ValidationError("El nombre de usuario no puede tener más de 20 caracteres.")
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            raise ValidationError("El nombre de usuario solo puede contener letras, números y guiones bajos.")
        
        if self.instance.pk:
            if User.objects.exclude(pk=self.instance.pk).filter(username=username).exists():
                raise ValidationError("Este nombre de usuario ya está en uso.")
        else:
            if User.objects.filter(username=username).exists():
                raise ValidationError("Este nombre de usuario ya está en uso.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if not email:
            raise ValidationError("El correo electrónico es obligatorio.")
        if len(email) > 150:
            raise ValidationError("El correo electrónico no puede tener más de 150 caracteres.")
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            raise ValidationError("Ingrese un correo electrónico válido.")
        
        if self.instance.pk:
            if User.objects.exclude(pk=self.instance.pk).filter(email=email).exists():
                raise ValidationError("Este correo electrónico ya está en uso.")
        else:
            if User.objects.filter(email=email).exists():
                raise ValidationError("Este correo electrónico ya está en uso.")
        return email

    def clean_first_name(self):
        first_name = self.cleaned_data.get('first_name', '').strip()
        if not first_name:
            raise ValidationError("El nombre es obligatorio.")
        if len(first_name) > 50:
            raise ValidationError("El nombre no puede tener más de 50 caracteres.")
        if not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$', first_name):
            raise ValidationError("El nombre solo puede contener letras.")
        return first_name

    def clean_last_name(self):
        last_name = self.cleaned_data.get('last_name', '').strip()
        if not last_name:
            raise ValidationError("El apellido es obligatorio.")
        if len(last_name) > 50:
            raise ValidationError("El apellido no puede tener más de 50 caracteres.")
        if not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$', last_name):
            raise ValidationError("El apellido solo puede contener letras.")
        return last_name

    def clean_password(self):
        password = self.cleaned_data.get('password', '')
        if self.is_edit and not password:
            return password
        
        if not password:
            if not self.is_edit:
                raise ValidationError("La contraseña es obligatoria.")
            return password
            
        if len(password) < 8:
            raise ValidationError("La contraseña debe tener al menos 8 caracteres.")
        if len(password) > 20:
            raise ValidationError("La contraseña no debe tener más de 20 caracteres.")
        if not re.search(r'[A-Z]', password):
            raise ValidationError("La contraseña debe contener al menos una letra mayúscula.")
        if not re.search(r'[a-z]', password):
            raise ValidationError("La contraseña debe contener al menos una letra minúscula.")
        if not re.search(r'[0-9]', password):
            raise ValidationError("La contraseña debe contener al menos un número.")
        return password


class PerfilForm(forms.ModelForm):
    class Meta:
        model = Perfil
        fields = ["run", "telefono", "direccion", "rol"]
        widgets = {
            "run":       forms.TextInput(attrs={"class": "form-control", "placeholder": "12345678-9"}),
            "telefono":  forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej: +56 9 1234 5678"}),
            "direccion": forms.TextInput(attrs={"class": "form-control", "placeholder": "Calle, número, ciudad"}),
            "rol":       forms.Select(attrs={"class": "form-select"}),
        }

    def validar_rut_chileno(self, rut):
        """Valida formato y dígito verificador de RUT chileno. Acepta k o K"""
        # Normalizar: convertir a mayúsculas y quitar puntos y guiones
        rut = rut.upper().replace(".", "").replace("-", "").strip()
        
        # Validar formato: 7-8 dígitos seguidos de número o K
        if not re.match(r'^\d{7,8}[0-9Kk]$', rut, re.IGNORECASE):
            return False
        
        rut_numeros = rut[:-1]
        dv = rut[-1]
        
        if not rut_numeros.isdigit():
            return False
        
        reversed_digits = map(int, reversed(rut_numeros))
        factors = [2, 3, 4, 5, 6, 7]
        s = sum(d * factors[i % 6] for i, d in enumerate(reversed_digits))
        resto = s % 11
        dv_calculado = 11 - resto
        
        if dv_calculado == 11:
            dv_esperado = '0'
        elif dv_calculado == 10:
            dv_esperado = 'K'
        else:
            dv_esperado = str(dv_calculado)
        
        return dv == dv_esperado

    def clean_run(self):
        run = self.cleaned_data.get('run', '').strip()
        if not run:
            raise ValidationError("El RUN/DNI es obligatorio.")
        
        # Validar RUT chileno
        if not self.validar_rut_chileno(run):
            raise ValidationError("RUT inválido. Formato: 12345678-9")
        
        # Normalizar formato
        run_limpio = run.upper().replace(".", "").replace("-", "").strip()
        run_formateado = f"{run_limpio[:-1]}-{run_limpio[-1]}"
        
        # Verificar unicidad
        if self.instance.pk:
            if Perfil.objects.exclude(pk=self.instance.pk).filter(run=run_formateado).exists():
                raise ValidationError("Este RUT ya está registrado.")
        else:
            if Perfil.objects.filter(run=run_formateado).exists():
                raise ValidationError("Este RUT ya está registrado.")
        
        return run_formateado

    def clean_telefono(self):
        telefono = self.cleaned_data.get('telefono', '').strip()
        if telefono and not re.match(r'^[\d\s\+\-\(\)]+$', telefono):
            raise ValidationError("El teléfono solo puede contener números y los símbolos +, -, (, ).")
        return telefono

class PerfilAuthForm(AuthenticationForm):
    username = forms.CharField(
        label="Usuario",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Nombre de usuario"})
    )
    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Contraseña"})
    )

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if not username:
            raise ValidationError("El nombre de usuario es obligatorio.")
        return username

    def clean_password(self):
        password = self.cleaned_data.get('password', '')
        if not password:
            raise ValidationError("La contraseña es obligatoria.")
        return password

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

    def clean_fecha_ingreso(self):
        fecha = self.cleaned_data.get('fecha_ingreso')
        if fecha and fecha > date.today():
            raise ValidationError("La fecha de ingreso no puede ser futura.")
        return fecha

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

    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre', '').strip()
        if not nombre:
            raise ValidationError("El nombre de la disciplina es obligatorio.")
        
        if self.instance.pk:
            if Disciplina.objects.exclude(pk=self.instance.pk).filter(nombre=nombre).exists():
                raise ValidationError("Ya existe una disciplina con este nombre.")
        else:
            if Disciplina.objects.filter(nombre=nombre).exists():
                raise ValidationError("Ya existe una disciplina con este nombre.")
        return nombre


class ActividadDeportivaForm(forms.ModelForm):
    estudiantes = forms.ModelMultipleChoiceField(
        queryset=Estudiante.objects.none(),     # ← Importante
        required=False,
        widget=forms.CheckboxSelectMultiple
    )

    class Meta:
        model = ActividadDeportiva
        fields = [
            'nombre', 'disciplina', 'fecha_inicio', 'fecha_fin',
            'lugar', 'tipo', 'estudiantes'
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'disciplina': forms.Select(attrs={'class': 'form-select'}),
            'fecha_inicio': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'fecha_fin': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'lugar': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        disciplina_id = None

        # 1. Extraer disciplina del POST o initial
        if "data" in kwargs and kwargs["data"].get("disciplina"):
            disciplina_id = kwargs["data"].get("disciplina")
        elif "initial" in kwargs and kwargs["initial"].get("disciplina"):
            disciplina_id = kwargs["initial"].get("disciplina")

        super().__init__(*args, **kwargs)

        # 2. Actualizar queryset basado en la disciplina
        if disciplina_id:
            self.fields['estudiantes'].queryset = Estudiante.objects.filter(
                inscripciones__disciplina_id=disciplina_id,
                inscripciones__estado="ACTIVA",
            ).distinct()
        else:
            self.fields['estudiantes'].queryset = Estudiante.objects.none()

    # Tus validadores originales
    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre', '').strip()
        if not nombre:
            raise ValidationError("El nombre de la actividad es obligatorio.")
        return nombre

    def clean_fecha_inicio(self):
        fecha_inicio = self.cleaned_data.get('fecha_inicio')
        if not fecha_inicio:
            raise ValidationError("La fecha de inicio es obligatoria.")
        if fecha_inicio < date.today():
            raise ValidationError("La fecha de inicio no puede ser anterior a hoy.")
        return fecha_inicio

    def clean_lugar(self):
        lugar = self.cleaned_data.get('lugar', '').strip()
        if not lugar:
            raise ValidationError("El lugar es obligatorio.")
        return lugar

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
        self.fields['estudiante'].queryset = (
            Estudiante.objects
            .filter(perfil__activo=True)
            .select_related('perfil__user')
            .order_by('perfil__user__last_name', 'perfil__user__first_name')
        )

class SeleccionarAlumnosForm(forms.Form):
    estudiantes = forms.ModelMultipleChoiceField(
        queryset=Estudiante.objects.all().order_by("perfil__user__username"),
        widget=forms.CheckboxSelectMultiple,
        required=True
    )