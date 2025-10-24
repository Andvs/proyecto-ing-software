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
from django.db import transaction
from django.forms import formset_factory
from django.utils import timezone

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


@rol_requerido(roles_permitidos=['Entrenador', 'Admin'])
def asistencia_index(request):
    form = SeleccionarActividadForm(request.GET or None)

    # Si hay parámetros (el usuario pulsó Continuar), valida
    if request.GET:
        if form.is_valid():
            actividad = form.cleaned_data['actividad']
            return redirect('asistencia_marcar', actividad_id=actividad.id)
        # si no es válido, cae a render con errores

    return render(request, 'asistencia/seleccionar.html', {'form': form})


@rol_requerido(roles_permitidos=['Entrenador', 'Admin'])
def asistencia_marcar(request, actividad_id):
    """
    Paso 2: tabla de jugadores de la disciplina de la actividad con radios Presente/Ausente.
    Requiere marcar TODOS (el formset obliga 'estado' requerido).
    """
    actividad = get_object_or_404(ActividadDeportiva, pk=actividad_id)
    disciplina = actividad.disciplina

    # Jugadores correspondientes a la disciplina (y activos)
    # Usamos Rendimiento como vínculo Estudiante-Disciplina
    estudiantes = (Estudiante.objects
                .filter(activo=True, rendimiento__disciplina=disciplina)
                .distinct()
                .order_by('apellido', 'nombre'))

    # Si no hay vínculo rendimiento/disciplinas aún, podrías optar por:
    # estudiantes = Estudiante.objects.filter(activo=True).order_by('apellido','nombre')

    # QUIÉN MARCA: tomamos el Usuario (tu modelo propio) desde la sesión
    usuario_id = request.session.get('usuario_id')
    usuario = Usuario.objects.filter(pk=usuario_id).first()
    marcador = usuario.nombre_usuario if usuario else "Desconocido"

    initial = [
        {
            'estudiante_id': e.id,
            'alumno': f"{e.apellido}, {e.nombre}",
        }
        for e in estudiantes
    ]

    Formset = AsistenciaFormSet
    if request.method == 'POST':
        formset = Formset(request.POST, initial=initial)
        if formset.is_valid():
            # Validar que todos tengan estado (el campo es required)
            faltantes = [f for f in formset if not f.cleaned_data.get('estado')]
            if faltantes:
                messages.error(request, "Debes marcar Presente/Ausente para todos los jugadores.")
            else:
                with transaction.atomic():
                    registros = []
                    for f in formset:
                        est_id = f.cleaned_data['estudiante_id']
                        estado = f.cleaned_data['estado']
                        est = Estudiante.objects.filter(pk=est_id).first()

                        # upsert por (estudiante, actividad)
                        obj, _created = Asistencia.objects.update_or_create(
                            estudiante=est,
                            actividad_deportiva=actividad,
                            defaults={
                                'estado': estado,
                                'fecha_hora_marcaje': timezone.now(),
                                'estudiante_nombre': f"{est.nombre} {est.apellido}" if est else "",
                                # Si luego conectas Entrenador real, rellenas el FK.
                                'entrenador': None,
                                'entrenador_nombre': marcador,
                            }
                        )
                        registros.append(obj)
                messages.success(request, f"Asistencia guardada para {len(registros)} jugadores. Marcada por {marcador}.")
                return redirect('asistencia_resumen', actividad_id=actividad.id)
        else:
            messages.error(request, "Corrige los errores del formulario.")
    else:
        formset = Formset(initial=initial)

    contexto = {
        'actividad': actividad,
        'disciplina': disciplina,
        'formset': formset,
        'marcador': marcador,
    }
    return render(request, 'asistencia/marcar.html', contexto)


@rol_requerido(roles_permitidos=['Entrenador', 'Admin'])
def asistencia_resumen(request, actividad_id):
    actividad = get_object_or_404(ActividadDeportiva, pk=actividad_id)
    registros = (Asistencia.objects
                .filter(actividad_deportiva=actividad)
                .select_related('estudiante'))
    return render(request, 'asistencia/resumen.html', {
        'actividad': actividad,
        'registros': registros,
    })