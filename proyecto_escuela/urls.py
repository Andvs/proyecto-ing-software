from django.contrib import admin
from django.urls import path
from app import views as v

urlpatterns = [
    path('admin/', admin.site.urls),

    # --- Auth + dashboard ---
    path('', v.index, name='index'),
    path('login/', v.login_view, name='login'),
    path('logout/', v.logout_view, name='logout'),
    path('dashboard/', v.dashboard, name='dashboard'),

    # --- Usuarios ---
    path('usuarios/', v.lista_usuarios, name='lista_usuarios'),
    path('usuarios/registrar/', v.registrar_usuario, name='registrar'),
    path('usuarios/editar/<int:pk>/', v.editar_usuario, name='editar_usuario'),
    path('usuarios/toggle-activo/<int:pk>/', v.perfil_toggle_activo, name='toggle_activo'),

    # --- Disciplinas ---
    path('disciplinas/crear/', v.crear_disciplina, name='crear_disciplina'),
    path('disciplinas/', v.lista_disciplinas, name='lista_disciplinas'),
    path('disciplinas/editar/<int:pk>/', v.editar_disciplina, name='editar_disciplina'),
    path('disciplinas/eliminar/<int:pk>/', v.eliminar_disciplina, name='eliminar_disciplina'),
    
    # --- Actividades ---
    path('actividades/crear/', v.crear_actividad, name='crear_actividad'),
    path('actividades/', v.lista_actividades, name='lista_actividades'),
    path('actividades/editar/<int:pk>/', v.editar_actividad, name='editar_actividad'),
    path('actividades/eliminar/<int:pk>/', v.eliminar_actividad, name='eliminar_actividad'),
    
    # --- Inscripciones ---
    path('inscripciones/crear/', v.crear_inscripcion, name='crear_inscripcion'),
    path('inscripciones/', v.lista_inscripciones, name='lista_inscripciones'),
    path('inscripciones/editar/<int:pk>/', v.editar_inscripcion, name='editar_inscripcion'),
    path('inscripciones/eliminar/<int:pk>/', v.eliminar_inscripcion, name='eliminar_inscripcion'),
    
    # --- Asistencia ---
    path('asistencia/', v.asistencia_listar, name='asistencia_listar'),
    path('asistencia/nueva/', v.asistencia_seleccionar, name='asistencia_seleccionar'),
    path('asistencia/<int:actividad_id>/marcar/', v.asistencia_marcar, name='asistencia_marcar'),
    path('asistencia/<int:actividad_id>/<str:fecha>/editar/', v.asistencia_editar, name='asistencia_editar'),
    path('asistencia/<int:actividad_id>/<str:fecha>/ver/', v.asistencia_ver_estudiantes, name='asistencia_ver_estudiantes'),
    path('asistencia/<int:actividad_id>/<str:fecha>/toggle/', v.asistencia_toggle_activa, name='asistencia_toggle_activa'),
]