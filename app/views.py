from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password
from .forms import *
from .models import *
from .decorators import *
from django.views.decorators.http import require_POST
from django.urls import reverse

# Create your views here.
def index(request):
    return render(request,"index.html")

def login(request):
    if request.method == "POST":
        nombre_usuario = request.POST.get('nombre_usuario')
        contraseña_plana = request.POST.get('contraseña')
        
        try:
            usuario = Usuario.objects.get(nombre_usuario=nombre_usuario)
            
            # ✅ --- ESTA ES LA LÍNEA CORREGIDA ---
            # Usamos check_password de Django, que sabe cómo leer el hash de la base de datos.
            if check_password(contraseña_plana, usuario.contraseña):
                
                # Guardamos el ID del usuario en la sesión
                request.session['usuario_id'] = usuario.id
                
                messages.success(request, f"¡Bienvenido, {usuario.nombre_usuario}!")
                return redirect('dashboard')
            else:
                messages.error(request, "La contraseña es incorrecta.")

        except Usuario.DoesNotExist:
            messages.error(request, "El usuario no existe.")
        
        # Si algo falla, redirigimos de nuevo al login
        return redirect('login')

    return render(request, 'login.html')

# SE COMENTÓ LA LINEA DE FORMA TEMPORAL PARA TESTING
# DEBIDO A LA CARENCIA DE USUARIO Y ROLES PRECARGADOS EN LA BASE - Cam-99
@rol_requerido(roles_permitidos=['Admin', 'Entrenador', 'Coordinador Deportivo', 'Estudiante'])
def dashboard(request):
    return render(request,"dashboard.html")

# SE COMENTÓ LA LINEA DE FORMA TEMPORAL PARA TESTING
# DEBIDO A LA CARENCIA DE USUARIO Y ROLES PRECARGADOS EN LA BASE - Cam-99
@rol_requerido(roles_permitidos=['Admin'])
def formulario(request):
    if request.method == "POST":
        form = UsuarioForm(request.POST)
        if form.is_valid():
            usuario = form.save(commit=False)
            contraseña_plana = form.cleaned_data['contraseña']
            usuario.contraseña = make_password(contraseña_plana)
            usuario.save()
            messages.success(request, "Usuario creado correctamente")
            return redirect("formulario")
    else:
        form = UsuarioForm()
    return render(request, "usuarios/formulario.html", {"form": form})


@rol_requerido(roles_permitidos=['Admin'])
def lista_usuarios(request):
    roles = Rol.objects.all()
    query = request.GET.get('q')
    usuarios_list = Usuario.objects.all().order_by('id')
    if query:
        # Consulta base para los campos de texto
        text_query = (
            Q(nombre_usuario__icontains=query) |
            Q(rol__nombre__icontains=query) # Asumiendo que 'rol' tiene un campo 'nombre'
        )
        # INICIO: Lógica para buscar por el campo booleano 'activo'
        query_lower = query.lower()
        
        # Palabras que el usuario podría escribir para buscar 'activos'
        palabras_activo = ['si', 'sí', 'activo', 'activos', 'true', '1']
        
        # Palabras que el usuario podría escribir para buscar 'inactivos'
        palabras_inactivo = ['no', 'inactivo', 'inactivos', 'false', '0']
        if query_lower in palabras_activo:
            # Si busca "activo", combinamos la búsqueda de texto CON la condición booleana
            final_query = text_query | Q(activo=True)
        elif query_lower in palabras_inactivo:
            # Si busca "inactivo", combinamos la búsqueda de texto CON la condición booleana
            final_query = text_query | Q(activo=False)
        else:
            # Si no es una palabra booleana, solo buscamos en los campos de texto
            final_query = text_query
        
        # FIN de la lógica para el campo 'activo'
            
        usuarios_list = usuarios_list.filter(final_query).distinct()
    
    paginator = Paginator(usuarios_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': query,
    }
    return render(request, 'usuarios/lista.html', context)

@rol_requerido(roles_permitidos=['Admin'])
def editarUsuario(request, usuario_id):
    usuario = get_object_or_404(Usuario, pk=usuario_id)
    if request.method == 'POST':
        form = UsuarioEditForm(request.POST, instance=usuario)
        if form.errors:
            messages.error(request,f"Ese nombre de Usuario ya exite")
        if form.is_valid():
            form.save()
            messages.success(request,f"¡Usuario '{usuario.nombre_usuario}' su rol fue cambiado con exito! por '{usuario.rol}'")
            messages.success(request, f'¡Usuario "{usuario.nombre_usuario}" actualizado correctamente!')
            return redirect('lista_usuarios')
    else:
        form = UsuarioEditForm(instance=usuario)
    context = {
        'form': form,
        'usuario': usuario,
    }
    return render(request, 'usuarios/editar.html', context)

@require_POST
def deshabilitar_usuario(request, pk):
    """
    Alterna el booleano 'activo' del Usuario (modelo propio).
    No elimina, solo habilita/deshabilita. Vuelve a la misma página.
    """
    usuario = get_object_or_404(Usuario, pk=pk)
    usuario.activo = not usuario.activo
    usuario.save(update_fields=["activo"])

    nombre = getattr(usuario, "nombre_usuario", str(usuario))
    estado = "habilitado" if usuario.activo else "deshabilitado"
    messages.success(request, f'El usuario «{nombre}» fue {estado} correctamente.')

    return redirect(request.POST.get("next") or reverse("lista_usuarios"))