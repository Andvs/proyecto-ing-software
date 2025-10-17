from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password
from .form import *
from .models import *
# Create your views here.
def index(request):
    return render(request,"index.html")

def login(request):
    return render(request, 'login.html')

def dashboard(request):
    return render(request,"dashboard.html")

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

def lista_usuarios(request):
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