from django.contrib import admin
from django.urls import path
from app import views as v
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', v.index, name="index"),
    path('login/', v.login, name='login'),
    path('dashboard/', v.dashboard, name="dashboard"),
    path('formulario/', v.formulario, name="formulario"),
    path('usuarios/', v.lista_usuarios, name='lista_usuarios'),
    path('usuarios/editar/<int:usuario_id>/', v.editarUsuario, name='editar_usuario'),
    path("usuarios/<int:pk>/toggle-activo/", v.deshabilitar_usuario, name="deshabilitar_usuario"),

    path('asistencia/', v.asistencia_index, name='asistencia_index'),
    path('asistencia/<int:actividad_id>/marcar/', v.asistencia_marcar, name='asistencia_marcar'),
    path('asistencia/<int:actividad_id>/resumen/', v.asistencia_resumen, name='asistencia_resumen'),
]
