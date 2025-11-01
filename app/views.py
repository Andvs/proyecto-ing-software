# usuarios/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.urls import reverse
from django.db import transaction
from django.utils import timezone


from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required

# Formularios
from .forms import *

# Modelos
from .models import *

# Decorador
from .decorators import rol_requerido


# ============== PÚBLICAS / AUTH ==============
def index(request):
    return render(request, "index.html")


def login_view(request):
    """
    Login usando auth de Django + chequeo de Perfil.activo.
    Espera en el form: username, password.
    """
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        user = authenticate(request, username=username, password=password)
        if user is None:
            messages.error(request, "Usuario o contraseña inválidos.")
            return redirect("login")

        # Chequeo Perfil.activo (si existe Perfil)
        try:
            perfil = user.perfil
            if not perfil.activo:
                messages.error(request, "Tu cuenta está deshabilitada. Contacta a un administrador.")
                return redirect("login")
        except Perfil.DoesNotExist:
            pass

        auth_login(request, user)
        messages.success(request, f"¡Bienvenido, {user.get_full_name() or user.username}!")
        return redirect("dashboard")

    return render(request, "login.html")


@login_required
def logout_view(request):
    auth_logout(request)
    messages.info(request, "Sesión cerrada correctamente.")
    return redirect("login")


# ============== PRIVADAS (DASHBOARD + USUARIOS) ==============
@rol_requerido(roles_permitidos=['Admin', 'Entrenador', 'Coordinador Deportivo', 'Estudiante'])
def dashboard(request):
    return render(request, "dashboard.html")


@rol_requerido(roles_permitidos=['Admin'])
def registrar_usuario(request):
    if request.method == 'POST':
        # Botón "Cancelar"
        if request.POST.get('cancelar'):
            return redirect('dashboard')

        user_form   = UserForm(request.POST)
        perfil_form = PerfilForm(request.POST)
        est_form    = EstudianteForm(request.POST)

        user_ok   = user_form.is_valid()
        perfil_ok = perfil_form.is_valid()

        # ¿Rol = Estudiante?
        rol_es_estudiante = False
        if perfil_ok:
            rol_sel = perfil_form.cleaned_data.get('rol')
            if rol_sel and getattr(rol_sel, "nombre", "").strip().lower() == 'estudiante':
                rol_es_estudiante = True

        est_ok = (not rol_es_estudiante) or est_form.is_valid()

        if user_ok and perfil_ok and est_ok:
            with transaction.atomic():
                # 1) User
                user = user_form.save(commit=False)
                raw_password = user.password
                user.set_password(raw_password)
                user.save()

                # 2) Perfil
                perfil = perfil_form.save(commit=False)
                perfil.user = user
                perfil.save()

                # 3) Estudiante (opcional)
                if rol_es_estudiante:
                    Estudiante.objects.update_or_create(
                        perfil=perfil,
                        defaults={
                            'curso': est_form.cleaned_data['curso'],
                            'fecha_ingreso': est_form.cleaned_data['fecha_ingreso'],
                        },
                    )

            messages.success(request, "Usuario registrado correctamente.")
            return redirect('lista_usuarios')
        else:
            messages.error(request, "Revisa los datos del formulario.")
    else:
        user_form   = UserForm()
        perfil_form = PerfilForm()
        est_form    = EstudianteForm()

    return render(request, 'usuarios/registrar.html', {
        'user_form': user_form,
        'perfil_form': perfil_form,
        'est_form': est_form,
    })


@rol_requerido(roles_permitidos=['Admin'])
def lista_usuarios(request):
    """
    Listado con búsqueda por username/nombre/apellido/run/rol
    y filtro por activo/inactivo (palabras naturales).
    """
    q = (request.GET.get("q") or "").strip()

    perfiles = Perfil.objects.select_related("user", "rol").order_by("user__username")

    if q:
        q_lower = q.lower()
        palabras_activo = {"si", "sí", "true", "1", "activo", "activos"}
        palabras_inactivo = {"no", "false", "0", "inactivo", "inactivos"}

        text_q = (
            Q(user__username__icontains=q) |
            Q(user__first_name__icontains=q) |
            Q(user__last_name__icontains=q) |
            Q(run__icontains=q) |
            Q(telefono__icontains=q) |
            Q(direccion__icontains=q) |
            Q(rol__nombre__icontains=q)
        )

        if q_lower in palabras_activo:
            perfiles = perfiles.filter(text_q | Q(activo=True))
        elif q_lower in palabras_inactivo:
            perfiles = perfiles.filter(text_q | Q(activo=False))
        else:
            perfiles = perfiles.filter(text_q)

    paginator = Paginator(perfiles, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "usuarios/lista.html", {
        "page_obj": page_obj,
        "search_query": q,
    })


@rol_requerido(roles_permitidos=['Admin'])
@require_POST
def perfil_toggle_activo(request, pk: int):
    """
    Alterna Perfil.activo (no toca User.is_active).
    Redirige a la misma URL (mantiene paginación y búsqueda).
    """
    perfil = get_object_or_404(Perfil.objects.select_related("user"), pk=pk)
    perfil.activo = not perfil.activo
    perfil.save(update_fields=["activo"])

    nombre = perfil.user.get_full_name() or perfil.user.username
    estado = "habilitado" if perfil.activo else "deshabilitado"
    messages.success(request, f'El usuario «{nombre}» fue {estado} correctamente.')

    return redirect(request.POST.get("next") or reverse("lista_usuarios"))


@rol_requerido(roles_permitidos=['Admin'])
def editar_usuario(request, pk):
    perfil = get_object_or_404(Perfil.objects.select_related("user", "rol"), pk=pk)
    if request.method == "POST":
        user_form = UserForm(request.POST, instance=perfil.user)
        if not request.POST.get("password"):
            # si no enviaron password, elimina el campo para no sobrescribirlo
            user_form.fields.pop("password", None)

        perfil_form = PerfilForm(request.POST, instance=perfil)

        if user_form.is_valid() and perfil_form.is_valid():
            user = user_form.save(commit=False)
            if "password" in user_form.cleaned_data and user_form.cleaned_data["password"]:
                user.set_password(user_form.cleaned_data["password"])
            user.save()

            perfil_form.save()
            messages.success(request, "Usuario actualizado correctamente.")
            return redirect("lista_usuarios")
        else:
            messages.error(request, "Revisa los datos del formulario.")
    else:
        user_form = UserForm(instance=perfil.user)
        if "password" in user_form.fields:
            user_form.fields["password"].widget.attrs["placeholder"] = "Dejar en blanco para no cambiar"
        perfil_form = PerfilForm(instance=perfil)

    return render(request, "usuarios/editar.html", {
        "perfil": perfil,
        "user_form": user_form,
        "perfil_form": perfil_form,
    })


@rol_requerido(roles_permitidos=['Entrenador', 'Admin'])
def asistencia_seleccionar(request):
    """
    Paso 1: seleccionar Disciplina y Actividad.
    """
    disciplinas = Disciplina.objects.all().order_by("nombre")
    # por simplicidad mostramos todas; puedes filtrar por disc. con JS si quieres
    actividades = ActividadDeportiva.objects.select_related("disciplina").all().order_by("-fecha_inicio")

    if request.method == "POST":
        disc_id = request.POST.get("disciplina")
        act_id = request.POST.get("actividad")

        if not disc_id or not act_id:
            messages.error(request, "Selecciona una disciplina y una actividad.")
            return redirect("asistencia_seleccionar")

        actividad = get_object_or_404(ActividadDeportiva, pk=act_id)
        if str(actividad.disciplina_id) != str(disc_id):
            messages.error(request, "La actividad no pertenece a la disciplina seleccionada.")
            return redirect("asistencia_seleccionar")

        return redirect("asistencia_marcar", actividad_id=actividad.id)

    return render(request, "asistencia/seleccionar.html", {
        "disciplinas": disciplinas,
        "actividades": actividades,
    })


@rol_requerido(roles_permitidos=['Entrenador', 'Admin'])
def asistencia_marcar(request, actividad_id: int):
    actividad = get_object_or_404(ActividadDeportiva.objects.select_related("disciplina"), pk=actividad_id)
    disciplina = actividad.disciplina
    inscripciones = (Inscripcion.objects
                    .select_related("estudiante__perfil__user", "disciplina")
                    .filter(disciplina=disciplina, estado="ACTIVA", estudiante__perfil__activo=True)
                    .order_by("estudiante__perfil__user__last_name", "estudiante__perfil__user__first_name"))
    estudiantes = [insc.estudiante for insc in inscripciones]
    hoy = timezone.localdate()

    if request.method == "POST":
        # ⚠️ Asegura que el usuario que marca tenga Perfil
        try:
            marcaje_por = request.user.perfil
        except Perfil.DoesNotExist:
            messages.error(request, "Tu usuario no tiene Perfil asociado. No es posible registrar asistencia.")
            return redirect("dashboard")

        if not estudiantes:
            messages.info(request, "No hay estudiantes inscritos para esta disciplina. No hay nada que guardar.")
            return redirect("asistencia_seleccionar")

        presentes_ids = set(map(int, request.POST.getlist("presentes")))

        with transaction.atomic():
            Asistencia.objects.filter(
                actividad=actividad,
                fecha_hora_marcaje__date=hoy
            ).delete()

            ahora = timezone.now()
            creados = 0
            for est in estudiantes:
                if est.perfil_id in presentes_ids:
                    Asistencia.objects.create(
                        usuario=est.perfil,
                        actividad=actividad,
                        fecha_hora_marcaje=ahora,
                        marcaje_por=marcaje_por,  # ✅ siempre con Perfil válido
                        entrenador=marcaje_por if marcaje_por.rol.nombre == "Entrenador" else None,
                    )
                    creados += 1

        messages.success(request, f"Asistencia guardada exitosamente. Presentes: {creados}.")
        return redirect("dashboard")

    presentes_ids_hoy = set(
        Asistencia.objects.filter(actividad=actividad, fecha_hora_marcaje__date=hoy)
        .values_list("usuario_id", flat=True)
    )
    return render(request, "asistencia/marcar.html", {
        "actividad": actividad,
        "disciplina": disciplina,
        "estudiantes": estudiantes,
        "presentes_ids_hoy": presentes_ids_hoy,
    })
@rol_requerido(roles_permitidos=['Entrenador', 'Admin'])
def crear_disciplina(request):
    if request.method == 'POST':
        # Si el método es POST, procesamos el formulario
        form = DisciplinaForm(request.POST)
        if form.is_valid():
            form.save() # Guarda el objeto en la base de datos
            # Añade un mensaje de éxito
            messages.success(request, '¡Disciplina registrada con éxito!')
            # Redirige a la lista de disciplinas (cambia 'lista_disciplinas' por tu URL)
            return redirect('lista_disciplinas') 
    else:
        # Si el método es GET, mostramos un formulario vacío
        form = DisciplinaForm()
    # Pasamos el formulario al contexto de la plantilla
    context = {
        'form': form
    }
    return render(request, 'disiplina/crear.html', context)
@rol_requerido(roles_permitidos=['Entrenador', 'Admin'])
def lista_disciplinas(request):
    # 1. Obtener el término de búsqueda
    search_query = request.GET.get('q', '')
    
    # 2. Queryset base
    disciplinas_list = Disciplina.objects.all().order_by('nombre')

    # 3. Aplicar filtro de búsqueda si existe
    if search_query:
        disciplinas_list = disciplinas_list.filter(
            Q(nombre__icontains=search_query) |
            Q(descripcion__icontains=search_query)
        )

    # 4. Configurar paginación
    paginator = Paginator(disciplinas_list, 10) # 10 disciplinas por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
    }
    return render(request, 'disiplina/lista.html', context)
@rol_requerido(roles_permitidos=['Entrenador', 'Admin'])
def editar_disciplina(request, pk):
    # 1. Obtenemos la disciplina que queremos editar (o mostramos 404 si no existe)
    disciplina = get_object_or_404(Disciplina, pk=pk)

    if request.method == 'POST':
        # 2. Si se envía el formulario, lo procesamos con los datos nuevos
        #    pasando la 'instance' para que sepa qué objeto actualizar.
        form = DisciplinaForm(request.POST, instance=disciplina)
        if form.is_valid():
            form.save() # Guarda los cambios en el objeto existente
            messages.success(request, '¡Disciplina actualizada con éxito!')
            return redirect('lista_disciplinas') # Vuelve a la lista
    else:
        # 3. Si es GET, creamos el formulario y le pasamos la 'instance'
        #    para que muestre los datos actuales de esa disciplina.
        form = DisciplinaForm(instance=disciplina)

    context = {
        'form': form
    }
    # 4. Renderizamos una plantilla (podemos crear una nueva o reutilizar la de crear)
    #    Vamos a crear una nueva para que el título sea "Editar"
    return render(request, 'disiplina/editar.html', context)

@require_POST # Súper importante para la seguridad en eliminaciones
def eliminar_disciplina(request, pk):
    disciplina = get_object_or_404(Disciplina, pk=pk)
    
    try:
        nombre_disciplina = disciplina.nombre
        disciplina.delete() # Borra el objeto de la base de datos
        messages.success(request, f'¡Disciplina "{nombre_disciplina}" eliminada con éxito!')
    except Exception as e:
        messages.error(request, f'Error al eliminar la disciplina: {e}')

    # Redirigimos de vuelta a la lista
    # (El script ya no envía 'next', así que redirigimos a la lista principal)
    return redirect('lista_disciplinas')