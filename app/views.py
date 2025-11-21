# usuarios/views.py
from django.http import JsonResponse
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

from app.forms import *
from app.models import *
from app.decorators import rol_requerido


# ============== PÚBLICAS / AUTH ==============
def index(request):
    return render(request, "index.html")


def login_view(request):
    if request.method == "POST":
        form = PerfilAuthForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
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
        else:
            messages.error(request, "Usuario o contraseña inválidos.")
    else:
        form = PerfilAuthForm()
    
    return render(request, "login.html", {"form": form})


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
        if request.POST.get('cancelar'):
            return redirect('dashboard')

        user_form   = UserForm(request.POST, is_edit=False)
        perfil_form = PerfilForm(request.POST)
        est_form    = EstudianteForm(request.POST)

        user_ok   = user_form.is_valid()
        perfil_ok = perfil_form.is_valid()

        rol_es_estudiante = False
        if perfil_ok:
            rol_sel = perfil_form.cleaned_data.get('rol')
            if rol_sel and getattr(rol_sel, "nombre", "").strip().lower() == 'estudiante':
                rol_es_estudiante = True

        est_ok = (not rol_es_estudiante) or est_form.is_valid()

        if user_ok and perfil_ok and est_ok:
            try:
                with transaction.atomic():
                    user = user_form.save(commit=False)
                    raw_password = user_form.cleaned_data['password']
                    user.set_password(raw_password)
                    user.save()

                    perfil = perfil_form.save(commit=False)
                    perfil.user = user
                    perfil.save()

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
            except Exception as e:
                messages.error(request, f"Error al registrar usuario: {str(e)}")
        else:
            messages.error(request, "Revisa los datos del formulario.")
    else:
        user_form   = UserForm(is_edit=False)
        perfil_form = PerfilForm()
        est_form    = EstudianteForm()

    return render(request, 'usuarios/registrar.html', {
        'user_form': user_form,
        'perfil_form': perfil_form,
        'est_form': est_form,
    })


@rol_requerido(roles_permitidos=['Admin'])
def lista_usuarios(request):
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
        user_form = UserForm(request.POST, instance=perfil.user, is_edit=True)
        perfil_form = PerfilForm(request.POST, instance=perfil)

        if user_form.is_valid() and perfil_form.is_valid():
            try:
                with transaction.atomic():
                    user = user_form.save(commit=False)
                    password = user_form.cleaned_data.get("password")
                    if password:
                        user.set_password(password)
                    user.save()
                    perfil_form.save()
                    
                messages.success(request, "Usuario actualizado correctamente.")
                return redirect("lista_usuarios")
            except Exception as e:
                messages.error(request, f"Error al actualizar usuario: {str(e)}")
        else:
            messages.error(request, "Revisa los datos del formulario.")
    else:
        user_form = UserForm(instance=perfil.user, is_edit=True)
        perfil_form = PerfilForm(instance=perfil)

    return render(request, "usuarios/editar.html", {
        "perfil": perfil,
        "user_form": user_form,
        "perfil_form": perfil_form,
    })
    
    
# -----------------------------------------------------
# ASISTENCIA (con Sesión) 
# -----------------------------------------------------

def _query_sesiones_asistencia(filtros):
    qs = (SesionAsistencia.objects
          .select_related('actividad__disciplina', 'marcaje_por__user'))

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


@rol_requerido(roles_permitidos=['Entrenador', 'Admin'])
def asistencia_listar(request):
    disciplinas = Disciplina.objects.all().order_by('nombre')
    actividades = ActividadDeportiva.objects.select_related('disciplina').order_by('-fecha_inicio')

    filtros = {
        'disciplina': request.GET.get('disciplina') or None,
        'actividad':  request.GET.get('actividad') or None,
        'desde':      request.GET.get('desde') or None,
        'hasta':      request.GET.get('hasta') or None,
        'estudiante_q': request.GET.get('q') or '',
    }

    try:
        if filtros['desde']:
            filtros['desde'] = datetime.strptime(filtros['desde'], '%Y-%m-%d').date()
        if filtros['hasta']:
            filtros['hasta'] = datetime.strptime(filtros['hasta'], '%Y-%m-%d').date()
    except ValueError:
        messages.error(request, "Formato de fechas inválido (usa AAAA-MM-DD).")
        return redirect('asistencia_listar')
    
    # ==== Validación rango consistente ====
    if filtros['desde'] and filtros['hasta'] and filtros['desde'] > filtros['hasta']:
        messages.error(
            request,
            "El rango de fechas es inconsistente: 'Desde' no puede ser mayor que 'Hasta'."
        )
        return redirect('asistencia_listar')

    sesiones = _query_sesiones_asistencia(filtros)

    context = {
        'disciplinas': disciplinas,
        'actividades': actividades,
        'sesiones': sesiones,
        'filtros': filtros,
    }
    return render(request, 'asistencia/listar.html', context)


@rol_requerido(roles_permitidos=['Entrenador', 'Admin'])
def asistencia_ver_estudiantes(request, actividad_id: int, fecha: str):
    fecha_date = datetime.strptime(fecha, '%Y-%m-%d').date()
    actividad = get_object_or_404(ActividadDeportiva, pk=actividad_id)
    sesion = get_object_or_404(SesionAsistencia, actividad=actividad, fecha=fecha_date)

    # Presentes (tal como estaba)
    presentes_qs = (
        sesion.detalles
        .select_related('usuario__user')
        .order_by('usuario__user__last_name', 'usuario__user__first_name')
    )

    presentes_count = presentes_qs.count()
    presentes_perfil_ids = set(
        presentes_qs.values_list('usuario_id', flat=True)
    )

    # ==== Estudiantes esperados según tipo de actividad ====
    if actividad.tipo == "torneo":
        # Usa los estudiantes asignados al torneo
        estudiantes_qs = (
            actividad.estudiantes
            .select_related("perfil__user")
            .filter(perfil__activo=True)
            .order_by("perfil__user__last_name", "perfil__user__first_name")
        )
        estudiantes = list(estudiantes_qs)
    else:
        # Usa inscripciones activas de la disciplina
        inscripciones = (
            Inscripcion.objects
            .select_related("estudiante__perfil__user", "disciplina")
            .filter(
                disciplina=actividad.disciplina,
                estado="ACTIVA",
                estudiante__perfil__activo=True,
            )
            .order_by(
                "estudiante__perfil__user__last_name",
                "estudiante__perfil__user__first_name",
            )
        )
        estudiantes = [insc.estudiante for insc in inscripciones]

    # ==== Ausentes: estudiantes cuyo perfil no está en la lista de presentes ====
    ausentes = [
        est for est in estudiantes
        if est.perfil_id not in presentes_perfil_ids
    ]
    ausentes_count = len(ausentes)

    return render(request, 'asistencia/estudiantes.html', {
        'actividad': actividad,
        'fecha': fecha_date,
        'sesion': sesion,
        'detalles': presentes_qs,
        'presentes_count': presentes_count,
        'ausentes': ausentes,
        'ausentes_count': ausentes_count,
    })



@rol_requerido(roles_permitidos=['Entrenador', 'Admin'])
def asistencia_editar(request, actividad_id: int, fecha: str):
    request.GET = request.GET.copy()
    request.GET['fecha'] = fecha
    return asistencia_marcar(request, actividad_id)


@rol_requerido(roles_permitidos=['Entrenador', 'Admin'])
@require_POST
def asistencia_toggle_activa(request, actividad_id: int, fecha: str):
    fecha_date = datetime.strptime(fecha, '%Y-%m-%d').date()
    actividad = get_object_or_404(ActividadDeportiva, pk=actividad_id)
    sesion = get_object_or_404(SesionAsistencia, actividad=actividad, fecha=fecha_date)

    sesion.activo = not sesion.activo
    sesion.save(update_fields=["activo"])

    estado = "habilitada" if sesion.activo else "deshabilitada"
    messages.success(request, f"La sesión del {fecha_date:%d-%m-%Y} fue {estado} correctamente.")
    return redirect(request.POST.get("next") or "asistencia_listar")



# … tus otros imports …

@rol_requerido(roles_permitidos=['Entrenador', 'Admin'])
def asistencia_marcar(request, actividad_id: int):
    actividad = get_object_or_404(
        ActividadDeportiva.objects.select_related("disciplina"),
        pk=actividad_id
    )
    disciplina = actividad.disciplina

    # ==== HOY: siempre en horario local (America/Santiago) ====
    hoy = timezone.localdate()   # <--- USAMOS ESTO COMO "hoy"

    # ==== NO permitir asistencia antes de que comience la actividad ====
    if actividad.fecha_inicio and hoy < actividad.fecha_inicio:
        messages.error(
            request,
            f"No puedes registrar asistencia porque la actividad aún no comienza "
            f"(inicio: {actividad.fecha_inicio:%d-%m-%Y})."
        )
        return redirect("asistencia_listar")

    # ▬▬▬▬▬ OBTENER ESTUDIANTES ▬▬▬▬▬
    if actividad.tipo == "torneo":
        estudiantes_qs = (
            actividad.estudiantes
            .select_related("perfil__user")
            .filter(perfil__activo=True)
            .order_by(
                "perfil__user__last_name",
                "perfil__user__first_name",
            )
        )
        estudiantes = list(estudiantes_qs)
    else:
        inscripciones = (
            Inscripcion.objects
            .select_related("estudiante__perfil__user", "disciplina")
            .filter(
                disciplina=disciplina,
                estado="ACTIVA",
                estudiante__perfil__activo=True,
            )
            .order_by(
                "estudiante__perfil__user__last_name",
                "estudiante__perfil__user__first_name",
            )
        )
        estudiantes = [insc.estudiante for insc in inscripciones]

    # ---------------- FECHA DE LA SESIÓN ----------------
    fecha_param = (request.GET.get('fecha') or request.GET.get('date') or None)
    if fecha_param:
        try:
            fecha_obj = datetime.strptime(fecha_param, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, "Fecha inválida (usa AAAA-MM-DD).")
            return redirect("asistencia_listar")
    else:
        # si no viene parámetro, usamos el "hoy" local
        fecha_obj = hoy

    # Validar que la fecha de sesión esté dentro del rango de la actividad
    inicio = actividad.fecha_inicio
    fin = actividad.fecha_fin  # puede ser None

    if inicio and fecha_obj < inicio:
        messages.error(
            request,
            f"La asistencia no puede marcarse antes del inicio de la actividad "
            f"({inicio:%d-%m-%Y})."
        )
        return redirect("asistencia_listar")

    if fin and fecha_obj > fin:
        messages.error(
            request,
            f"La asistencia no puede marcarse después del fin de la actividad "
            f"({fin:%d-%m-%Y})."
        )
        return redirect("asistencia_listar")

    # Quién marca la asistencia
    try:
        marcaje_por = request.user.perfil
    except Perfil.DoesNotExist:
        marcaje_por = None

    # En GET: solo buscamos sesión existente, NO la creamos
    sesion = SesionAsistencia.objects.filter(actividad=actividad).first()

    # ---------------- GUARDAR ASISTENCIA (POST) ----------------
    if request.method == "POST":
        if not estudiantes:
            messages.info(request, "No hay estudiantes inscritos para esta disciplina.")
            return redirect("asistencia_seleccionar")

        # Crear sesión SOLO cuando se pulsa "Guardar asistencia"
        if sesion is None:
            sesion = SesionAsistencia.objects.create(
                actividad=actividad,
                fecha=fecha_obj,
                marcaje_por=marcaje_por,
                entrenador=(
                    marcaje_por if (marcaje_por and marcaje_por.rol.nombre == "Entrenador")
                    else None
                ),
            )
        else:
            # Actualizar campos si estaban vacíos / distinta fecha
            campos_modificados = []
            if sesion.fecha != fecha_obj:
                sesion.fecha = fecha_obj
                campos_modificados.append("fecha")
            if sesion.marcaje_por is None and marcaje_por is not None:
                sesion.marcaje_por = marcaje_por
                campos_modificados.append("marcaje_por")
            if sesion.entrenador is None and (marcaje_por and marcaje_por.rol.nombre == "Entrenador"):
                sesion.entrenador = marcaje_por
                campos_modificados.append("entrenador")
            if campos_modificados:
                campos_modificados.append("actualizado_en")
                sesion.save(update_fields=campos_modificados)

        # IDs de estudiantes presentes desde el formulario
        presentes_ids = set(map(int, request.POST.getlist("presentes")))

        with transaction.atomic():
            # Borrar marcajes anteriores de esta sesión
            Asistencia.objects.filter(sesion=sesion).delete()

            ahora = timezone.now()
            creados = 0
            for est in estudiantes:
                if est.perfil_id in presentes_ids:
                    Asistencia.objects.create(
                        sesion=sesion,
                        usuario=est.perfil,
                        actividad=actividad,
                        fecha_hora_marcaje=ahora,
                        marcaje_por=marcaje_por or sesion.marcaje_por,
                        entrenador=sesion.entrenador,
                    )
                    creados += 1

        messages.success(
            request,
            f"Asistencia del {fecha_obj:%d-%m-%Y} guardada. Presentes: {creados}."
        )
        return redirect("asistencia_listar")

    # ---------------- VISTA (GET) ----------------
    if sesion:
        presentes_ids_fecha = set(
            Asistencia.objects.filter(sesion=sesion)
            .values_list("usuario_id", flat=True)
        )
        fecha_contexto = sesion.fecha
    else:
        presentes_ids_fecha = set()
        fecha_contexto = fecha_obj

    return render(request, "asistencia/marcar.html", {
        "actividad": actividad,
        "disciplina": disciplina,
        "estudiantes": estudiantes,
        "presentes_ids_hoy": presentes_ids_fecha,
        "fecha_obj": fecha_contexto,
    })



@rol_requerido(roles_permitidos=['Entrenador', 'Admin'])
def asistencia_seleccionar(request):
    disciplinas = Disciplina.objects.all().order_by("nombre")

    disc_sel = request.GET.get("disciplina") or request.POST.get("disciplina")

    actividades_qs = (ActividadDeportiva.objects
                      .select_related("disciplina")
                      .order_by("-fecha_inicio"))

    if disc_sel:
        actividades_qs = actividades_qs.filter(disciplina_id=disc_sel)

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

        if str(actividad.disciplina_id) != str(disc_sel):
            messages.error(request, "La actividad no pertenece a la disciplina seleccionada.")
            return render(request, "asistencia/seleccionar.html", {
                "disciplinas": disciplinas,
                "actividades": actividades_qs,
                "disc_sel": disc_sel,
            })

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


# -----------------------------------------------------
# ACTIVIDADES DEPORTIVAS
# -----------------------------------------------------
@rol_requerido(roles_permitidos=['Entrenador', 'Admin', 'Coordinador Deportivo'])
def crear_actividad(request):

    print("\n========== DEBUG ==========")
    print("POST RECIBIDO:", request.POST)
    print("===========================\n")

    tipo = request.POST.get("tipo", "")
    disciplina_id = request.POST.get("disciplina")

    estudiantes_filtrados = Estudiante.objects.none()

    # Si es torneo y tiene disciplina → filtrar
    if tipo == "torneo" and disciplina_id:
        estudiantes_filtrados = Estudiante.objects.filter(
            inscripciones__disciplina_id=disciplina_id,
            inscripciones__estado="ACTIVA"
        ).distinct()

        print("ESTUDIANTES FILTRADOS:", estudiantes_filtrados)

    # Si POST
    if request.method == "POST":
        form = ActividadDeportivaForm(request.POST)

        # ← ← ← EL FIX IMPORTANTE
        form.fields["estudiantes"].queryset = estudiantes_filtrados

        if form.is_valid():
            actividad = form.save()

            if tipo == "torneo":
                seleccionados = form.cleaned_data["estudiantes"]
                print("ESTUDIANTES SELECCIONADOS:", seleccionados)

            messages.success(request, "Actividad registrada correctamente.")
            return redirect("lista_actividades")

        else:
            print("\n❌ FORMULARIO INVÁLIDO:")
            print(form.errors)
            print("=======================\n")

    else:
        form = ActividadDeportivaForm()

    # Set queryset cuando GET
    form.fields["estudiantes"].queryset = estudiantes_filtrados

    return render(request, "actividades/crear.html", {
        "form": form,
    })

@rol_requerido(roles_permitidos=['Entrenador', 'Admin', 'Coordinador Deportivo'])
def lista_actividades(request):
    search_query = request.GET.get('q', '')
    actividades_list = ActividadDeportiva.objects.select_related('disciplina').order_by('-fecha_inicio')

    if search_query:
        actividades_list = actividades_list.filter(
            Q(nombre__icontains=search_query) |
            Q(disciplina__nombre__icontains=search_query) |
            Q(lugar__icontains=search_query)
        )

    paginator = Paginator(actividades_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'actividades/lista.html', {
        'page_obj': page_obj,
        'search_query': search_query,
    })


@rol_requerido(roles_permitidos=['Entrenador', 'Admin', 'Coordinador Deportivo'])
def editar_actividad(request, pk):
    actividad = get_object_or_404(ActividadDeportiva, pk=pk)
    if request.method == 'POST':
        form = ActividadDeportivaForm(request.POST, instance=actividad)
        if form.is_valid():
            form.save()
            messages.success(request, '¡Actividad deportiva actualizada con éxito!')
            return redirect('lista_actividades')
    else:
        form = ActividadDeportivaForm(instance=actividad)
    return render(request, 'actividades/editar.html', {'form': form, 'actividad': actividad})


@require_POST
def eliminar_actividad(request, pk):
    actividad = get_object_or_404(ActividadDeportiva, pk=pk)
    try:
        nombre_actividad = actividad.nombre
        actividad.delete()
        messages.success(request, f'¡Actividad "{nombre_actividad}" eliminada con éxito!')
    except Exception as e:
        messages.error(request, f'Error al eliminar la actividad: {e}')
    return redirect('lista_actividades')


# -----------------------------------------------------
# INSCRIPCIONES
# -----------------------------------------------------
@rol_requerido(roles_permitidos=['Admin', 'Coordinador Deportivo'])
def crear_inscripcion(request):
    if request.method == 'POST':
        form = InscripcionForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, '¡Estudiante inscrito con éxito!')
                return redirect('lista_inscripciones')
            except Exception as e:
                messages.error(request, f'Error al inscribir: {e}')
    else:
        form = InscripcionForm()
    return render(request, 'inscripciones/crear.html', {'form': form})


@rol_requerido(roles_permitidos=['Admin', 'Coordinador Deportivo', 'Entrenador'])
def lista_inscripciones(request):
    search_query = request.GET.get('q', '')
    inscripciones_list = Inscripcion.objects.select_related(
        'estudiante__perfil__user', 
        'disciplina'
    ).order_by('-fecha_inscripcion')

    if search_query:
        inscripciones_list = inscripciones_list.filter(
            Q(estudiante__perfil__user__first_name__icontains=search_query) |
            Q(estudiante__perfil__user__last_name__icontains=search_query) |
            Q(estudiante__perfil__user__username__icontains=search_query) |
            Q(disciplina__nombre__icontains=search_query)
        )

    paginator = Paginator(inscripciones_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'inscripciones/lista.html', {
        'page_obj': page_obj,
        'search_query': search_query,
    })


@rol_requerido(roles_permitidos=['Admin', 'Coordinador Deportivo'])
def editar_inscripcion(request, pk):
    inscripcion = get_object_or_404(Inscripcion, pk=pk)
    if request.method == 'POST':
        form = InscripcionForm(request.POST, instance=inscripcion)
        if form.is_valid():
            form.save()
            messages.success(request, '¡Inscripción actualizada con éxito!')
            return redirect('lista_inscripciones')
    else:
        form = InscripcionForm(instance=inscripcion)
    return render(request, 'inscripciones/editar.html', {'form': form, 'inscripcion': inscripcion})


@rol_requerido(roles_permitidos=['Admin', 'Coordinador Deportivo'])
@require_POST
def eliminar_inscripcion(request, pk):
    inscripcion = get_object_or_404(Inscripcion, pk=pk)
    try:
        estudiante = inscripcion.estudiante.perfil.user.get_full_name()
        disciplina = inscripcion.disciplina.nombre
        inscripcion.delete()
        messages.success(request, f'¡Inscripción de {estudiante} en {disciplina} eliminada con éxito!')
    except Exception as e:
        messages.error(request, f'Error al eliminar la inscripción: {e}')
    return redirect('lista_inscripciones')

def obtener_estudiantes_por_disciplina(request, disciplina_id):
    estudiantes = Estudiante.objects.filter(
        inscripciones__disciplina_id=disciplina_id,
        inscripciones__estado="ACTIVA"
    ).distinct()

    data = [
        {"id": est.id, "nombre": est.perfil.user.get_full_name()}
        for est in estudiantes
    ]

    return JsonResponse({"estudiantes": data})
