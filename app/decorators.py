# usuarios/decorators.py
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.conf import settings

from .models import Perfil

def rol_requerido(roles_permitidos=None, *, permitir_superuser=True):
    """
    Verifica:
      - Usuario autenticado (Django)
      - Tiene Perfil asociado
      - Perfil.activo == True
      - Perfil.rol.nombre ∈ roles_permitidos
    Opcional: superuser siempre pasa (permitir_superuser=True).
    """
    roles_permitidos = set(roles_permitidos or [])

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            # 1) Autenticación
            if not request.user.is_authenticated:
                messages.error(request, "Por favor, inicia sesión para acceder a esta página.")
                return redirect(settings.LOGIN_URL if hasattr(settings, "LOGIN_URL") else "login")

            # 2) Superusuario bypass (opcional)
            if permitir_superuser and request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            # 3) Perfil existente y activo
            try:
                perfil = request.user.perfil
            except Perfil.DoesNotExist:
                messages.error(request, "Tu cuenta no tiene perfil asociado. Contacta a un administrador.")
                return redirect("dashboard")

            if not perfil.activo:
                messages.error(request, "Tu cuenta está deshabilitada. Contacta a un administrador.")
                return redirect("login")

            # 4) Rol permitido
            rol_nombre = getattr(perfil.rol, "nombre", None)
            if rol_nombre in roles_permitidos:
                return view_func(request, *args, **kwargs)

            messages.error(request, "No tienes los permisos necesarios para ver esta página.")
            return redirect("dashboard")
        return _wrapped
    return decorator


def login_requerido(view_func):
    """
    Versión simple por si no quieres importar login_required de Django en todas partes.
    Mantiene el mismo estilo de mensajes.
    """
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Por favor, inicia sesión para acceder a esta página.")
            return redirect("login")
        return view_func(request, *args, **kwargs)
    return _wrapped
