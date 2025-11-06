from django.contrib import admin
from django.urls import path
from app import views as v   # ajusta 'app' al nombre real de tu app

urlpatterns = [
    path('admin/', admin.site.urls),

    # --- Auth + dashboard ---
    path('', v.index, name='index'),
    path('login/', v.login_view, name='login'),
    path('logout/', v.logout_view, name='logout'),
    path('dashboard/', v.dashboard, name='dashboard'),

    # --- Usuarios (sin namespace) ---
    path('usuarios/', v.lista_usuarios, name='lista_usuarios'),
    path('usuarios/registrar/', v.registrar_usuario, name='registrar'),
    path('usuarios/editar/<int:pk>/', v.editar_usuario, name='editar_usuario'),
    path('usuarios/toggle-activo/<int:pk>/', v.perfil_toggle_activo, name='toggle_activo'),

    # --- disiplina (sin namespace) ---
    path('disciplinas/crear/', v.crear_disciplina, name='crear_disciplina'),
    path('disciplinas/', v.lista_disciplinas, name='lista_disciplinas'),
    path('disciplinas/editar/<int:pk>/', v.editar_disciplina, name='editar_disciplina'),
    path('disciplinas/eliminar/<int:pk>/', v.eliminar_disciplina, name='eliminar_disciplina'),
    
    # --- asistencia
    path('asistencia/', v.asistencia_listar, name='asistencia_listar'),
    path('asistencia/nueva/', v.asistencia_seleccionar, name='asistencia_seleccionar'),
    path('asistencia/<int:actividad_id>/marcar/', v.asistencia_marcar, name='asistencia_marcar'),
    path('asistencia/<int:actividad_id>/<str:fecha>/editar/', v.asistencia_editar, name='asistencia_editar'),
    path('asistencia/<int:actividad_id>/<str:fecha>/ver/', v.asistencia_ver_estudiantes, name='asistencia_ver_estudiantes'),
    path('asistencia/<int:actividad_id>/<str:fecha>/toggle/', v.asistencia_toggle_activa, name='asistencia_toggle_activa'),
]