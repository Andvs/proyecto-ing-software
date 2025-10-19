from django.shortcuts import redirect
from django.contrib import messages
from .models import Usuario # Asegúrate de importar tu modelo Usuario

def rol_requerido(roles_permitidos=[]):
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            # ✅ ESTE BLOQUE ES LA SOLUCIÓN.
            # Primero, comprueba si la llave existe ANTES de intentar usarla.
            if 'usuario_id' not in request.session:
                messages.error(request, "Por favor, inicia sesión para acceder a esta página.")
                return redirect('login') # Si no existe, redirige y termina.

            # El resto del código solo se ejecuta si la sesión es válida.
            try:
                usuario_id = request.session['usuario_id']
                usuario_logueado = Usuario.objects.get(id=usuario_id)
            except Usuario.DoesNotExist:
                request.session.flush()
                messages.error(request, "Tu sesión no es válida. Inicia sesión de nuevo.")
                return redirect('login')

            if usuario_logueado.rol and usuario_logueado.rol.nombre in roles_permitidos:
                return view_func(request, *args, **kwargs)
            else:
                messages.error(request, "No tienes los permisos necesarios para ver esta página.")
                return redirect('dashboard')
        
        return wrapper
    return decorator
