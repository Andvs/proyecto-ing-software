# usuarios/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Count, Q, F
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.urls import reverse
from django.db import transaction
from django.utils import timezone
from datetime import datetime

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
    
    
# -----------------------------------------------------
# ASISTENCIA (con Sesión) 
# -----------------------------------------------------

# -----------------------------
# Helper: sesiones de asistencia (lista)
# -----------------------------
def _query_sesiones_asistencia(filtros):
    """
    Devuelve un QS de SesionAsistencia con conteo de presentes y
    datos básicos de actividad/disciplina/marcador.
    """
    qs = (SesionAsistencia.objects
          .select_related('actividad__disciplina', 'marcaje_por__user'))

    # Filtros: disciplina, actividad, desde, hasta, estudiante_q
    disc_id = filtros.get('disciplina')
    act_id  = filtros.get('actividad')
    f_ini   = filtros.get('desde')
    f_fin   = filtros.get('hasta')
    est_q   = (filtros.get('estudiante_q') or '').strip()

    if disc_id:
        qs = qs.filter(actividad__disciplina_id=disc_id)
    if act_id:
        qs = qs.filter(actividad_id=act_id)
    if f_ini:
        qs = qs.filter(fecha__gte=f_ini)
    if f_fin:
        qs = qs.filter(fecha__lte=f_fin)

    # Búsqueda por estudiante presente en la sesión
    if est_q:
        qs = qs.filter(
            Q(detalles__usuario__user__first_name__icontains=est_q) |
            Q(detalles__usuario__user__last_name__icontains=est_q)  |
            Q(detalles__usuario__user__username__icontains=est_q)
        )

    qs = (qs
          .annotate(presentes=Count('detalles', distinct=True))
          .order_by('-fecha', '-id'))
    return qs


# -----------------------------
# LISTAR sesiones
# -----------------------------
@rol_requerido(roles_permitidos=['Entrenador', 'Admin'])
def asistencia_listar(request):
    disciplinas = Disciplina.objects.all().order_by('nombre')
    actividades = ActividadDeportiva.objects.select_related('disciplina').order_by('-fecha_inicio')

    # Leer filtros del GET
    filtros = {
        'disciplina': request.GET.get('disciplina') or None,
        'actividad':  request.GET.get('actividad') or None,
        'desde':      request.GET.get('desde') or None,
        'hasta':      request.GET.get('hasta') or None,
        'estudiante_q': request.GET.get('q') or '',
    }

    # Normalizar fechas
    try:
        if filtros['desde']:
            filtros['desde'] = datetime.strptime(filtros['desde'], '%Y-%m-%d').date()
        if filtros['hasta']:
            filtros['hasta'] = datetime.strptime(filtros['hasta'], '%Y-%m-%d').date()
    except ValueError:
        messages.error(request, "Formato de fechas inválido (usa AAAA-MM-DD).")
        return redirect('asistencia_listar')

    sesiones = _query_sesiones_asistencia(filtros)

    context = {
        'disciplinas': disciplinas,
        'actividades': actividades,
        'sesiones': sesiones,
        'filtros': filtros,
    }
    return render(request, 'asistencia/listar.html', context)


# -----------------------------
# VER estudiantes presentes (por sesión)
# -----------------------------
@rol_requerido(roles_permitidos=['Entrenador', 'Admin'])
def asistencia_ver_estudiantes(request, actividad_id: int, fecha: str):
    fecha_date = datetime.strptime(fecha, '%Y-%m-%d').date()
    actividad = get_object_or_404(ActividadDeportiva, pk=actividad_id)
    sesion = get_object_or_404(SesionAsistencia, actividad=actividad, fecha=fecha_date)

    presentes_qs = (sesion.detalles
                    .select_related('usuario__user')
                    .order_by('usuario__user__last_name', 'usuario__user__first_name'))

    return render(request, 'asistencia/estudiantes.html', {
        'actividad': actividad,
        'fecha': fecha_date,
        'sesion': sesion,
        'detalles': presentes_qs,                 # <— lista (queryset)
        'presentes_count': presentes_qs.count(),  # <— entero
    })



# -----------------------------
# EDITAR (re-marcar) una sesión
# -----------------------------
@rol_requerido(roles_permitidos=['Entrenador', 'Admin'])
def asistencia_editar(request, actividad_id: int, fecha: str):
    """
    Reutiliza la pantalla de 'marcar', pero para una fecha concreta,
    asegurando que la sesión exista (aunque termine con 0 presentes).
    """
    request.GET = request.GET.copy()
    request.GET['fecha'] = fecha  # para reutilizar la misma vista
    return asistencia_marcar(request, actividad_id)


# -----------------------------
# CANCELAR una sesión (eliminar encabezado + detalles)
# -----------------------------

@rol_requerido(roles_permitidos=['Entrenador', 'Admin'])
@require_POST
def asistencia_toggle_activa(request, actividad_id: int, fecha: str):
    """
    Alterna el estado activo/inactivo de una sesión de asistencia.
    No elimina registros, solo marca como deshabilitada o habilitada.
    """
    fecha_date = datetime.strptime(fecha, '%Y-%m-%d').date()
    actividad = get_object_or_404(ActividadDeportiva, pk=actividad_id)
    sesion = get_object_or_404(SesionAsistencia, actividad=actividad, fecha=fecha_date)

    sesion.activo = not sesion.activo
    sesion.save(update_fields=["activo"])

    estado = "habilitada" if sesion.activo else "deshabilitada"
    messages.success(request, f"La sesión del {fecha_date:%d-%m-%Y} fue {estado} correctamente.")
    return redirect(request.POST.get("next") or "asistencia_listar")



# -----------------------------
# MARCAR/EDITAR asistencia (usa sesión)
# -----------------------------
@rol_requerido(roles_permitidos=['Entrenador', 'Admin'])
def asistencia_marcar(request, actividad_id: int):
    actividad = get_object_or_404(
        ActividadDeportiva.objects.select_related("disciplina"),
        pk=actividad_id
    )
    disciplina = actividad.disciplina

    inscripciones = (
        Inscripcion.objects
        .select_related("estudiante__perfil__user", "disciplina")
        .filter(
            disciplina=disciplina,
            estado="ACTIVA",
            estudiante__perfil__activo=True
        )
        .order_by(
            "estudiante__perfil__user__last_name",
            "estudiante__perfil__user__first_name"
        )
    )
    estudiantes = [insc.estudiante for insc in inscripciones]

    # fecha objetivo (?fecha=AAAA-MM-DD) — default: hoy
    fecha_param = (request.GET.get('fecha') or request.GET.get('date') or None)
    if fecha_param:
        try:
            fecha_obj = datetime.strptime(fecha_param, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, "Fecha inválida (usa AAAA-MM-DD).")
            return redirect("asistencia_listar")
    else:
        fecha_obj = timezone.localdate()

    # obtener/crear sesión (existe aunque queden 0 presentes)
    try:
        marcaje_por = request.user.perfil
    except Perfil.DoesNotExist:
        marcaje_por = None

    sesion, _created = SesionAsistencia.objects.get_or_create(
        actividad=actividad,
        defaults={
            'fecha': fecha_obj,
            'marcaje_por': marcaje_por,
            'entrenador': (
                marcaje_por if (marcaje_por and marcaje_por.rol.nombre == "Entrenador")
                else None
            ),
        }
    )
    # si ya existía y la fecha cambió (caso extremo), sincroniza metadatos
    if sesion.fecha != fecha_obj:
        sesion.fecha = fecha_obj
        if sesion.marcaje_por is None:
            sesion.marcaje_por = marcaje_por
        if sesion.entrenador is None and (marcaje_por and marcaje_por.rol.nombre == "Entrenador"):
            sesion.entrenador = marcaje_por
        sesion.save(update_fields=['fecha', 'marcaje_por', 'entrenador', 'actualizado_en'])

    if request.method == "POST":
        if not estudiantes:
            messages.info(request, "No hay estudiantes inscritos para esta disciplina.")
            return redirect("asistencia_seleccionar")

        presentes_ids = set(map(int, request.POST.getlist("presentes")))
        with transaction.atomic():
            # Reemplaza SOLO los detalles de esta sesión
            Asistencia.objects.filter(sesion=sesion).delete()

            # Hora real (aware). Django guardará en UTC; se mostrará en TZ con el filtro.
            ahora = timezone.now()
            creados = 0
            for est in estudiantes:
                if est.perfil_id in presentes_ids:
                    Asistencia.objects.create(
                        sesion=sesion,
                        usuario=est.perfil,
                        actividad=actividad,       # compatibilidad/reportes
                        fecha_hora_marcaje=ahora,  # hora real del marcaje
                        marcaje_por=marcaje_por or sesion.marcaje_por,
                        entrenador=sesion.entrenador,
                    )
                    creados += 1

        messages.success(
            request,
            f"Asistencia del {fecha_obj:%d-%m-%Y} guardada. Presentes: {creados}."
        )
        return redirect("asistencia_listar")

    # Checkboxes preseleccionados con lo ya marcado
    presentes_ids_fecha = set(
        Asistencia.objects.filter(sesion=sesion)
        .values_list("usuario_id", flat=True)
    )

    return render(request, "asistencia/marcar.html", {
        "actividad": actividad,
        "disciplina": disciplina,
        "estudiantes": estudiantes,
        "presentes_ids_hoy": presentes_ids_fecha,
        "fecha_obj": sesion.fecha,
    })


# -----------------------------
# Seleccionar disciplina/actividad (excluye ocupadas)
# -----------------------------
@rol_requerido(roles_permitidos=['Entrenador', 'Admin'])
def asistencia_seleccionar(request):
    """
    Paso 1: seleccionar Disciplina y Actividad.
    - Muestra SOLO actividades que NO tengan sesión creada.
    - POST valida y redirige a marcar.
    """
    disciplinas = Disciplina.objects.all().order_by("nombre")

    # disciplina seleccionada (GET para filtrar en vivo; POST para envío final)
    disc_sel = request.GET.get("disciplina") or request.POST.get("disciplina")

    # Query base de actividades
    actividades_qs = (ActividadDeportiva.objects
                      .select_related("disciplina")
                      .order_by("-fecha_inicio"))

    if disc_sel:
        actividades_qs = actividades_qs.filter(disciplina_id=disc_sel)

    # Excluir actividades que YA tengan sesión
    ocupadas_ids = SesionAsistencia.objects.values_list("actividad_id", flat=True)
    actividades_qs = actividades_qs.exclude(id__in=ocupadas_ids)

    if request.method == "POST":
        act_id = request.POST.get("actividad")
        if not disc_sel or not act_id:
            messages.error(request, "Selecciona una disciplina y una actividad.")
            return render(request, "asistencia/seleccionar.html", {
                "disciplinas": disciplinas,
                "actividades": actividades_qs,
                "disc_sel": disc_sel,
            })

        actividad = get_object_or_404(ActividadDeportiva, pk=act_id)

        # Seguridad: actividad debe pertenecer a esa disciplina
        if str(actividad.disciplina_id) != str(disc_sel):
            messages.error(request, "La actividad no pertenece a la disciplina seleccionada.")
            return render(request, "asistencia/seleccionar.html", {
                "disciplinas": disciplinas,
                "actividades": actividades_qs,
                "disc_sel": disc_sel,
            })

        # Seguridad: bloquear si ya tiene sesión (por si fuerzan POST)
        if SesionAsistencia.objects.filter(actividad=actividad).exists():
            messages.warning(request, "Esta actividad ya tiene una asistencia registrada.")
            return render(request, "asistencia/seleccionar.html", {
                "disciplinas": disciplinas,
                "actividades": actividades_qs,
                "disc_sel": disc_sel,
            })

        return redirect("asistencia_marcar", actividad_id=actividad.id)

    return render(request, "asistencia/seleccionar.html", {
        "disciplinas": disciplinas,
        "actividades": actividades_qs,
        "disc_sel": disc_sel,
    })


# -----------------------------------------------------
# DISCIPLINA
# -----------------------------------------------------
@rol_requerido(roles_permitidos=['Entrenador', 'Admin', 'Coordinador Deportivo'])
def crear_disciplina(request):
    if request.method == 'POST':
        form = DisciplinaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '¡Disciplina registrada con éxito!')
            return redirect('lista_disciplinas')
    else:
        form = DisciplinaForm()
    return render(request, 'disiplina/crear.html', {'form': form})


@rol_requerido(roles_permitidos=['Entrenador', 'Admin', 'Coordinador Deportivo'])
def lista_disciplinas(request):
    search_query = request.GET.get('q', '')
    disciplinas_list = Disciplina.objects.all().order_by('nombre')

    if search_query:
        disciplinas_list = disciplinas_list.filter(
            Q(nombre__icontains=search_query) |
            Q(descripcion__icontains=search_query)
        )

    paginator = Paginator(disciplinas_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'disiplina/lista.html', {
        'page_obj': page_obj,
        'search_query': search_query,
    })

@rol_requerido(roles_permitidos=['Entrenador', 'Admin', 'Coordinador Deportivo'])
def editar_disciplina(request, pk):
    disciplina = get_object_or_404(Disciplina, pk=pk)
    if request.method == 'POST':
        form = DisciplinaForm(request.POST, instance=disciplina)
        if form.is_valid():
            form.save()
            messages.success(request, '¡Disciplina actualizada con éxito!')
            return redirect('lista_disciplinas')
    else:
        form = DisciplinaForm(instance=disciplina)
    return render(request, 'disiplina/editar.html', {'form': form})


@require_POST
def eliminar_disciplina(request, pk):
    disciplina = get_object_or_404(Disciplina, pk=pk)
    try:
        nombre_disciplina = disciplina.nombre
        disciplina.delete()
        messages.success(request, f'¡Disciplina "{nombre_disciplina}" eliminada con éxito!')
    except Exception as e:
        messages.error(request, f'Error al eliminar la disciplina: {e}')
    return redirect('lista_disciplinas')
