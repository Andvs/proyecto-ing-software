from django.contrib import admin
from django.urls import path
from app import views as v
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', v.index, name="index"),
    path('login/', v.login, name='login'),
    path('dashboard/', v.dashboard, name="dashboard"),
    path('formulario/', v.formulario, name="formulario"),
]
