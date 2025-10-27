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

    # --- Asistencia (sin namespace) ---
    path('asistencia/', v.asistencia_seleccionar, name='asistencia_seleccionar'),
    path('asistencia/<int:actividad_id>/marcar/', v.asistencia_marcar, name='asistencia_marcar'),
]