from django.urls import path
from app import views

app_name = "usuarios"

urlpatterns = [
    path("", views.lista_usuarios, name="lista"),
    path("registrar/", views.registrar_usuario, name="registrar"),
    path("<int:pk>/toggle-activo/", views.perfil_toggle_activo, name="toggle_activo"),
    # si más adelante agregas editar:
    path("<int:pk>/editar/", views.editar_usuario, name="editar"),
]