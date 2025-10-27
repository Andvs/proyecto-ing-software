# models.py
from django.contrib.auth.models import User
from django.db import models


class Rol(models.Model):
    nombre = models.CharField(max_length=45, unique=True)
    def __str__(self): return self.nombre
    class Meta:
        verbose_name_plural = "Roles"
        ordering = ["nombre"]


class Perfil(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    run = models.CharField("RUN/DNI", max_length=20, unique=True)
    telefono = models.CharField(max_length=20, blank=True)
    direccion = models.CharField(max_length=100, blank=True)
    rol = models.ForeignKey(Rol, on_delete=models.PROTECT)
    activo = models.BooleanField(default=True)
    def __str__(self): return f"{self.user.username} ({self.rol.nombre})"
    class Meta: ordering = ["user__username"]


class Curso(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    def __str__(self): return self.nombre
    class Meta: ordering = ["nombre"]


class Estudiante(models.Model):
    perfil = models.OneToOneField(Perfil, on_delete=models.CASCADE)
    curso = models.ForeignKey(Curso, on_delete=models.PROTECT)
    fecha_ingreso = models.DateField()
    def __str__(self): return f"{self.perfil.user.username} - {self.curso.nombre}"
    class Meta: ordering = ["perfil__user__username"]


class Disciplina(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.CharField(max_length=200, blank=True)
    def __str__(self): return self.nombre
    class Meta: ordering = ["nombre"]


class ActividadDeportiva(models.Model):
    nombre = models.CharField(max_length=50)
    disciplina = models.ForeignKey(Disciplina, on_delete=models.PROTECT)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True)
    lugar = models.CharField(max_length=100)
    def __str__(self): return f"{self.nombre} ({self.disciplina.nombre})"
    class Meta: ordering = ["-fecha_inicio"]


# NUEVO: Inscripción Estudiante↔Disciplina
class Inscripcion(models.Model):
    ESTADOS = [
        ('ACTIVA', 'Activa'),
        ('SUSPENDIDA', 'Suspendida'),
        ('BAJA', 'Baja'),
        ('FINALIZADA', 'Finalizada'),
    ]
    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE, related_name='inscripciones')
    disciplina = models.ForeignKey(Disciplina, on_delete=models.PROTECT, related_name='inscripciones')
    fecha_inscripcion = models.DateField(auto_now_add=True)
    estado = models.CharField(max_length=12, choices=ESTADOS, default='ACTIVA')

    class Meta:
        # Un estudiante no debe tener dos inscripciones a la misma disciplina simultáneamente.
        unique_together = [('estudiante', 'disciplina')]
        ordering = ['-fecha_inscripcion']

    def __str__(self):
        return f"{self.estudiante.perfil.user.username} → {self.disciplina.nombre} ({self.estado})"


class Asistencia(models.Model):
    usuario = models.ForeignKey(Perfil, on_delete=models.CASCADE, related_name="asistencias")
    actividad = models.ForeignKey(ActividadDeportiva, on_delete=models.PROTECT)
    fecha_hora_marcaje = models.DateTimeField()
    marcaje_por = models.ForeignKey(Perfil, on_delete=models.PROTECT, related_name="marcadas")
    entrenador = models.ForeignKey(Perfil, null=True, blank=True, on_delete=models.PROTECT, related_name="asistencias_dirigidas")

    class Meta:
        unique_together = [("usuario", "fecha_hora_marcaje", "actividad")]
        ordering = ["-fecha_hora_marcaje"]

    def __str__(self):
        return f"Asistencia de {self.usuario.user.username} en {self.actividad.nombre}"


class Rendimiento(models.Model):
    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE)
    disciplina = models.ForeignKey(Disciplina, on_delete=models.PROTECT)
    fecha = models.DateField()
    puntaje = models.IntegerField()
    observaciones = models.CharField(max_length=200, blank=True)

    class Meta:
        unique_together = [("estudiante", "disciplina", "fecha")]
        ordering = ["-fecha"]

    def __str__(self):
        return f"{self.estudiante.perfil.user.username} - {self.disciplina.nombre} ({self.puntaje})"
