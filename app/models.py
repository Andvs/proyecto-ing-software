from django.db import models
from django.conf import settings
from django_mysql.models import EnumField  
from django.core.validators import MinLengthValidator, MaxLengthValidator, RegexValidator

validar_contraseña = RegexValidator(
    regex=r'^(?=.*[A-Z])(?=.*[a-z]).*$',
    message='La contraseña debe tener al menos una letra mayúscula y una minúscula.'
)

solo_letras = RegexValidator(
    regex=r'^[A-Za-zÁÉÍÓÚáéíóúÑñ\s-]+$',
    message='El nombre de usuario solo puede contener letras, espacios o guiones.'
)


class Cargo(models.Model):
    nombre = models.CharField(max_length=45)
    descripcion = models.CharField(max_length=200, blank=True)
    def __str__(self): return self.nombre

class Rol(models.Model):
    nombre = models.CharField(max_length=45, unique=True)
    descripcion = models.CharField(max_length=200, null=True, blank=True)
    def __str__(self):
        return self.nombre

class Permiso(models.Model):
    nombre = models.CharField(max_length=45, unique=True)
    descripcion = models.CharField(max_length=200, null=True, blank=True)
    def __str__(self):
        return self.nombre

class Usuario(models.Model):
    nombre_usuario = models.CharField(max_length=50, unique=True)
    contraseña = models.CharField(max_length=128)
    activo = models.BooleanField(default=True)
    rol = models.ForeignKey(Rol, on_delete=models.PROTECT)
    def __str__(self):
        return self.nombre_usuario

class PermisoRol(models.Model):
    permiso = models.ForeignKey(Permiso, on_delete=models.CASCADE)
    rol = models.ForeignKey(Rol, on_delete=models.CASCADE)
    class Meta:
        unique_together = ('permiso', 'rol')

class Disciplina(models.Model):
    NOMBRES = (
        ("FUTBOL", "Fútbol"),
        ("BASQUETBOL", "Básquetbol"),
        ("VOLEIBOL", "Vóleibol"),
        ("ATLETISMO", "Atletismo"),
    )
    nombre = EnumField(choices=NOMBRES, default="FUTBOL", unique=True)
    descripcion = models.CharField(max_length=200, blank=True)
    def __str__(self): return self.get_nombre_display()


class Estudiante(models.Model):
    CURSOS = (
        ("8°", "Básico"),
        ("1°", "Primero"),
        ("2°", "Segundo"),
        ("3°", "Tercero"),
        ("4°", "Cuarto"),
    )
    run = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=50)
    apellido = models.CharField(max_length=50)
    fecha_nacimiento = models.DateField(null=True, blank=True)
    num_celular = models.CharField(max_length=10, blank=True)
    correo = models.EmailField(max_length=100, blank=True)

    # ENUM real
    curso = EnumField(choices=CURSOS, default="8°")

    fecha_ingreso = models.DateField(null=True, blank=True)
    activo = models.BooleanField(default=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL,
                                on_delete=models.SET_NULL, null=True, blank=True)
    def __str__(self): return f"{self.nombre} {self.apellido}"


class Entrenador(models.Model):
    run = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=50)
    apellido = models.CharField(max_length=50)
    fecha_nacimiento = models.DateField(null=True, blank=True)
    direccion = models.CharField(max_length=45, blank=True)
    num_celular = models.CharField(max_length=10, blank=True)
    correo = models.EmailField(max_length=100, blank=True)
    fecha_contratacion = models.DateField(null=True, blank=True)
    activo = models.BooleanField(default=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL,
                                on_delete=models.SET_NULL, null=True, blank=True)
    def __str__(self): return f"{self.nombre} {self.apellido}"


class EquipoAdministrativo(models.Model):
    run = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=50)
    apellido = models.CharField(max_length=50)
    fecha_nacimiento = models.DateField(null=True, blank=True)
    direccion = models.CharField(max_length=45, blank=True)
    num_celular = models.CharField(max_length=10, blank=True)
    correo = models.EmailField(max_length=100, blank=True)
    fecha_contratacion = models.DateField(null=True, blank=True)
    activo = models.BooleanField(default=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL,
                                on_delete=models.SET_NULL, null=True, blank=True)
    cargo = models.ForeignKey(Cargo, on_delete=models.PROTECT)
    def __str__(self): return f"{self.nombre} {self.apellido} ({self.cargo})"


class ActividadDeportiva(models.Model):
    TIPOS = (
        ("ENTRENAMIENTO", "Entrenamiento"),
        ("COMPETENCIA", "Competencia"),
        ("EVENTO", "Evento"),
        ("OTRO", "Otro"),
    )
    nombre = models.CharField(max_length=50)
    # ENUM real
    tipo = EnumField(choices=TIPOS, default="ENTRENAMIENTO")

    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    lugar = models.CharField(max_length=100)
    descripcion = models.CharField(max_length=400)
    disciplina = models.ForeignKey(Disciplina, on_delete=models.PROTECT)
    def __str__(self): return f"{self.nombre} ({self.get_tipo_display()})"


class Asistencia(models.Model):
    fecha_hora_marcaje = models.DateTimeField()
    estudiante = models.ForeignKey("Estudiante",
                                    on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name="asistencias")
    estudiante_nombre = models.CharField(max_length=120, blank=True)
    entrenador = models.ForeignKey("Entrenador",
                                    on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name="asistencias_marcadas")
    entrenador_nombre = models.CharField(max_length=120, blank=True)
    actividad_deportiva = models.ForeignKey("ActividadDeportiva",
                                            on_delete=models.PROTECT,
                                            related_name="asistencias")
    anotaciones = models.CharField(max_length=200, blank=True)

    def __str__(self):
        est = self.estudiante_nombre or (str(self.estudiante) if self.estudiante else "Estudiante eliminado")
        ent = self.entrenador_nombre or (str(self.entrenador) if self.entrenador else "Entrenador eliminado")
        return f"Asistencia de {est} en {self.actividad_deportiva} marcada por {ent} ({self.fecha_hora_marcaje:%Y-%m-%d %H:%M})"


class Rendimiento(models.Model):
    observaciones = models.CharField(max_length=200, blank=True)
    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE)
    disciplina = models.ForeignKey(Disciplina, on_delete=models.CASCADE)
    def __str__(self): return f"{self.estudiante} - {self.disciplina}"
