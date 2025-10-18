from .models import Usuario

def agregar_usuario_a_contexto(request):
    usuario = None
    if 'usuario_id' in request.session:
        try:
            usuario = Usuario.objects.get(id=request.session['usuario_id'])
        except Usuario.DoesNotExist:
            pass
    return {'user': usuario}