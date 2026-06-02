"""
Vistas del Panel de Administración Personalizado de Panimii Bakery.

Todas las vistas están protegidas con @staff_member_required,
que exige que el usuario tenga is_staff=True o is_superuser=True.
"""
from decimal import Decimal

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from catalogo.models import Orden, OrdenItem, Producto, Categoria

User = get_user_model()


# ── Helper: obtener hoy con timezone ────────────────────────────────────
def _hoy():
    hoy = timezone.localdate()
    return timezone.datetime(hoy.year, hoy.month, hoy.day,
                             tzinfo=timezone.get_current_timezone())


# ════════════════════════════════════════════════════════════════════════
# RESUMEN GENERAL (Dashboard principal)
# ════════════════════════════════════════════════════════════════════════

@staff_member_required(login_url='/auth/login/')
def resumen(request):
    """
    Vista principal del panel admin.

    Métricas:
    - Ventas del día (sum de totales de órdenes pagadas hoy)
    - Pedidos pendientes (pagadas pero no entregadas)
    - Galletas / unidades vendidas (total de ítems en órdenes pagadas)
    - Clientes registrados

    Tabla: últimas 5 órdenes recientes.
    """
    hoy = _hoy()

    # ── Métricas ──────────────────────────────────────────────────────
    ordenes_pagadas_hoy = Orden.objects.filter(
        estado__in=[Orden.Estado.PAGADA, Orden.Estado.EN_PROCESO,
                    Orden.Estado.ENVIADA, Orden.Estado.ENTREGADA],
        creado__gte=hoy,
    )
    ventas_dia = ordenes_pagadas_hoy.aggregate(
        total=Sum('total')
    )['total'] or Decimal('0.00')

    pedidos_pendientes = Orden.objects.filter(
        estado__in=[Orden.Estado.PAGADA, Orden.Estado.EN_PROCESO],
    ).count()

    # Unidades totales vendidas (en órdenes que ya fueron pagadas)
    unidades_vendidas = OrdenItem.objects.filter(
        orden__estado__in=[
            Orden.Estado.PAGADA, Orden.Estado.EN_PROCESO,
            Orden.Estado.ENVIADA, Orden.Estado.ENTREGADA,
        ]
    ).aggregate(total=Sum('cantidad'))['total'] or 0

    clientes_registrados = User.objects.filter(is_active=True).count()

    # ── Últimas 5 órdenes ─────────────────────────────────────────────
    ultimas_ordenes = (
        Orden.objects
        .select_related('cliente')
        .order_by('-creado')[:5]
    )

    ctx = {
        'ventas_dia':           ventas_dia,
        'pedidos_pendientes':   pedidos_pendientes,
        'unidades_vendidas':    unidades_vendidas,
        'clientes_registrados': clientes_registrados,
        'ultimas_ordenes':      ultimas_ordenes,
        'seccion_activa':       'resumen',
    }
    return render(request, 'panel_admin/resumen.html', ctx)


# ════════════════════════════════════════════════════════════════════════
# GESTIÓN DE PEDIDOS
# ════════════════════════════════════════════════════════════════════════

@staff_member_required(login_url='/auth/login/')
def pedidos(request):
    """Lista completa de órdenes con filtro por estado."""
    estado_filtro = request.GET.get('estado', '')
    ordenes = Orden.objects.select_related('cliente').order_by('-creado')
    if estado_filtro:
        ordenes = ordenes.filter(estado=estado_filtro)

    ctx = {
        'ordenes':        ordenes,
        'estado_filtro':  estado_filtro,
        'estados':        Orden.Estado.choices,
        'seccion_activa': 'pedidos',
    }
    return render(request, 'panel_admin/pedidos.html', ctx)


def enviar_correo_cambio_estado(orden, nuevo_estado, request):
    """
    Envía un correo HTML al cliente notificando el cambio de estado de su pedido.
    """
    from django.template.loader import render_to_string
    from django.core.mail import send_mail
    from django.conf import settings
    import logging
    logger = logging.getLogger(__name__)

    protocol = 'https' if request.is_secure() else 'http'
    domain = request.get_host()

    subject_map = {
        'pagada': f"¡Pago recibido! 🐻 Tu pedido #{orden.pk} está confirmado",
        'en_proceso': f"Tu pedido #{orden.pk} está en proceso de horneado 🥣",
        'enviada': f"¡Tu pedido va en camino! 🚴‍♂️ Orden #{orden.pk}",
        'entregada': f"¡Pedido entregado! 🐻 Gracias por tu compra - #{orden.pk}",
        'cancelada': f"Tu pedido #{orden.pk} ha sido cancelado",
    }
    
    asunto = subject_map.get(nuevo_estado, f"Actualización de tu pedido #{orden.pk} — Paniimi Bakery")

    # Mensajes personalizados según el estado
    mensajes = {
        'pagada': "Hemos registrado tu pago con éxito. Tus reposterías artesanales están listas o en proceso de horneado.",
        'en_proceso': "Nuestros reposteros ya están manos a la masa preparando tus roles y galletas favoritas.",
        'enviada': "¡Tu pedido ha salido de la cocina! Nuestro repartidor ya va en camino hacia tu dirección de entrega.",
        'entregada': "¡Tu pedido ha sido entregado! Esperamos de corazón que disfrutes cada bocado. ¡Gracias por elegir a Paniimi Bakery!",
        'cancelada': "Lamentamos informarte que tu pedido ha sido cancelado. Si tienes dudas, contáctanos respondiendo a este correo.",
    }
    
    mensaje_personalizado = mensajes.get(nuevo_estado, f"El estado de tu pedido ha cambiado a: {orden.get_estado_display()}")

    cuerpo = render_to_string('orden_estado_email.html', {
        'orden': orden,
        'estado_texto': orden.get_estado_display(),
        'mensaje_personalizado': mensaje_personalizado,
        'protocol': protocol,
        'domain': domain,
    })

    try:
        send_mail(
            subject=asunto,
            message="",
            html_message=cuerpo,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[orden.email_cliente],
            fail_silently=False,
        )
    except Exception as exc:
        logger.error('Error al enviar correo de cambio de estado %s para pedido #%s: %s', nuevo_estado, orden.pk, exc)


@staff_member_required(login_url='/auth/login/')
def detalle_pedido(request, orden_id):
    """Detalle completo de una orden y permite cambiar el estado de la misma."""
    orden = get_object_or_404(Orden.objects.select_related('cliente')
                              .prefetch_related('items__producto'), pk=orden_id)

    if request.method == 'POST':
        nuevo_estado = request.POST.get('estado')
        if nuevo_estado in Orden.Estado.values:
            if orden.estado != nuevo_estado:
                orden.estado = nuevo_estado
                orden.save(update_fields=['estado'])
                
                # Enviar correo de notificación de cambio de estado al cliente
                enviar_correo_cambio_estado(orden, nuevo_estado, request)
                
                messages.success(request, f'Estado del pedido #{orden.pk} actualizado a "{orden.get_estado_display()}" y correo enviado.')
            else:
                messages.info(request, 'El pedido ya tiene ese estado.')

    ctx = {
        'orden':          orden,
        'seccion_activa': 'pedidos',
        'estados':        Orden.Estado.choices,
    }
    return render(request, 'panel_admin/detalle_pedido.html', ctx)


# ════════════════════════════════════════════════════════════════════════
# INVENTARIO — CRUD completo
# ════════════════════════════════════════════════════════════════════════

from .forms import ProductoForm, CategoriaForm


@staff_member_required(login_url='/auth/login/')
def inventario(request):
    """Lista de productos con búsqueda y filtro de disponibilidad."""
    busqueda    = request.GET.get('q', '').strip()
    filtro_disp = request.GET.get('disponible', '')

    productos = Producto.objects.select_related('categoria').order_by('categoria__nombre', 'nombre')

    if busqueda:
        productos = productos.filter(nombre__icontains=busqueda)
    if filtro_disp == '1':
        productos = productos.filter(disponible=True)
    elif filtro_disp == '0':
        productos = productos.filter(disponible=False)

    ctx = {
        'productos':      productos,
        'busqueda':       busqueda,
        'filtro_disp':    filtro_disp,
        'seccion_activa': 'inventario',
    }
    return render(request, 'panel_admin/inventario.html', ctx)


@staff_member_required(login_url='/auth/login/')
def crear_producto(request):
    """Formulario para añadir un producto nuevo."""
    form = ProductoForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        producto = form.save()
        messages.success(request, f'Producto "{producto.nombre}" creado correctamente.')
        return redirect('panel_admin:inventario')

    ctx = {
        'form':           form,
        'titulo':         'Nuevo Producto',
        'seccion_activa': 'inventario',
    }
    return render(request, 'panel_admin/producto_form.html', ctx)


@staff_member_required(login_url='/auth/login/')
def editar_producto(request, producto_id):
    """Editar datos, imagen y stock de un producto existente."""
    producto = get_object_or_404(Producto, pk=producto_id)
    form = ProductoForm(request.POST or None, request.FILES or None, instance=producto)

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Producto "{producto.nombre}" actualizado.')
        return redirect('panel_admin:inventario')

    ctx = {
        'form':           form,
        'producto':       producto,
        'titulo':         f'Editar: {producto.nombre}',
        'seccion_activa': 'inventario',
    }
    return render(request, 'panel_admin/producto_form.html', ctx)


@staff_member_required(login_url='/auth/login/')
def eliminar_producto(request, producto_id):
    """
    GET  → confirmación.
    POST → elimina el producto (la imagen se borra del disco también).
    """
    producto = get_object_or_404(Producto, pk=producto_id)

    if request.method == 'POST':
        nombre = producto.nombre
        # Eliminar imagen del disco si existe
        if producto.imagen:
            import os
            if os.path.isfile(producto.imagen.path):
                os.remove(producto.imagen.path)
        producto.delete()
        messages.success(request, f'Producto "{nombre}" eliminado.')
        return redirect('panel_admin:inventario')

    ctx = {
        'producto':       producto,
        'seccion_activa': 'inventario',
    }
    return render(request, 'panel_admin/producto_confirmar_eliminar.html', ctx)



# ════════════════════════════════════════════════════════════════════════
# CLIENTES — CRUD completo
# ════════════════════════════════════════════════════════════════════════

from django.contrib import messages
from django.shortcuts import redirect

from .forms import CrearClienteForm, EditarClienteForm


@staff_member_required(login_url='/auth/login/')
def clientes(request):
    """Lista de todos los usuarios registrados (activos e inactivos)."""
    busqueda = request.GET.get('q', '').strip()
    usuarios = User.objects.order_by('-date_joined')
    if busqueda:
        usuarios = usuarios.filter(
            username__icontains=busqueda
        ) | usuarios.filter(
            email__icontains=busqueda
        ) | usuarios.filter(
            first_name__icontains=busqueda
        ) | usuarios.filter(
            last_name__icontains=busqueda
        )
        usuarios = usuarios.distinct()

    ctx = {
        'usuarios':       usuarios,
        'busqueda':       busqueda,
        'seccion_activa': 'clientes',
    }
    return render(request, 'panel_admin/clientes.html', ctx)


@staff_member_required(login_url='/auth/login/')
def crear_cliente(request):
    """Formulario para añadir un nuevo usuario desde el panel."""
    form = CrearClienteForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        usuario = form.save()
        messages.success(request, f'Usuario "{usuario.username}" creado correctamente.')
        return redirect('panel_admin:clientes')

    ctx = {
        'form':           form,
        'titulo':         'Nuevo Usuario',
        'seccion_activa': 'clientes',
    }
    return render(request, 'panel_admin/cliente_form.html', ctx)


@staff_member_required(login_url='/auth/login/')
def editar_cliente(request, user_id):
    """Editar datos y permisos de un usuario existente."""
    usuario = get_object_or_404(User, pk=user_id)
    form = EditarClienteForm(request.POST or None, instance=usuario)

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Usuario "{usuario.username}" actualizado.')
        return redirect('panel_admin:clientes')

    ctx = {
        'form':           form,
        'usuario':        usuario,
        'titulo':         f'Editar: {usuario.username}',
        'seccion_activa': 'clientes',
    }
    return render(request, 'panel_admin/cliente_form.html', ctx)


@staff_member_required(login_url='/auth/login/')
def eliminar_cliente(request, user_id):
    """
    GET  → página de confirmación.
    POST → elimina el usuario.
    Protecciones:
    - No puedes eliminarte a ti mismo.
    - No puedes eliminar al último superusuario.
    """
    usuario = get_object_or_404(User, pk=user_id)

    # Protección: no eliminarse a uno mismo
    if usuario == request.user:
        messages.error(request, 'No puedes eliminar tu propia cuenta.')
        return redirect('panel_admin:clientes')

    # Protección: último superusuario
    if usuario.is_superuser and User.objects.filter(is_superuser=True).count() <= 1:
        messages.error(request, 'No puedes eliminar el único superusuario del sistema.')
        return redirect('panel_admin:clientes')

    if request.method == 'POST':
        nombre = usuario.username
        usuario.delete()
        messages.success(request, f'Usuario "{nombre}" eliminado.')
        return redirect('panel_admin:clientes')

    ctx = {
        'usuario':        usuario,
        'seccion_activa': 'clientes',
    }
    return render(request, 'panel_admin/cliente_confirmar_eliminar.html', ctx)


@staff_member_required(login_url='/auth/login/')
def estaciones(request):
    """
    Gestiona el cambio de temporada/estación para la tienda de forma global.
    """
    from catalogo.models import ConfiguracionTemporada
    from django.contrib import messages
    from django.shortcuts import redirect

    # Obtener el registro Singleton de configuración
    config_obj, created = ConfiguracionTemporada.objects.get_or_create(
        pk=1,
        defaults={'temporada': ConfiguracionTemporada.Temporadas.ORIGINAL}
    )

    if request.method == 'POST':
        nueva_temporada = request.POST.get('temporada')
        if nueva_temporada in dict(ConfiguracionTemporada.Temporadas.choices):
            config_obj.temporada = nueva_temporada
            config_obj.save()
            
            # Mensajes personalizados de éxito inspirados en cada temporada
            mensajes = {
                'original': "¡Hemos vuelto al diseño original de Paniimi Bakery! 🖤",
                'primavera': "¡La primavera ha florecido en Paniimi Bakery! 🌸 Disfruta de la frescura en el sitio.",
                'verano': "¡El verano ha llegado a Paniimi Bakery! ☀️ Siente la calidez soleada en cada rincón.",
                'otono': "¡El otoño se siente en Paniimi Bakery! 🍂 Disfruta del cálido aroma del cacao y trigo.",
                'invierno': "¡El invierno ha cubierto Paniimi Bakery! ❄️ Disfruta de la acogedora dulzura de la temporada.",
            }
            messages.success(request, mensajes.get(nueva_temporada, "Configuración actualizada con éxito."))
        return redirect('panel_admin:estaciones')

    ctx = {
        'temporada_actual': config_obj.temporada,
        'seccion_activa': 'estaciones',
    }
    return render(request, 'panel_admin/estaciones.html', ctx)


@staff_member_required(login_url='/auth/login/')
def verificar_llave(request):
    """
    Pantalla premium donde el administrador debe subir su archivo .key.
    Valida la firma HMAC-SHA256 usando settings.SECRET_KEY.
    """
    from django.conf import settings
    from django.contrib import messages
    from django.shortcuts import render, redirect
    import hmac
    import hashlib

    # Si ya está verificado, redirigir directo al dashboard resumen
    if request.session.get('admin_key_verified', False):
        return redirect('panel_admin:resumen')

    if request.method == 'POST':
        key_file = request.FILES.get('keyfile')
        if not key_file:
            messages.error(request, 'Por favor, selecciona o arrastra tu archivo de llave (.key).')
            return redirect('panel_admin:verificar_llave')

        try:
            # Leer el contenido del archivo subido
            content = key_file.read().decode('utf-8').strip()
            
            # Formato esperado: "usuario:firma"
            if ':' not in content:
                raise ValueError('Formato de archivo inválido.')
                
            username, signature = content.split(':', 1)
            
            # La llave debe corresponder al usuario actualmente logueado
            if username != request.user.username:
                messages.error(request, 'Este archivo de llave pertenece a otro administrador.')
                return redirect('panel_admin:verificar_llave')

            # Calcular la firma HMAC-SHA256 correcta en el servidor
            msg = f"{username}:admin-key"
            expected_sig = hmac.new(
                settings.SECRET_KEY.encode(),
                msg.encode(),
                hashlib.sha256
            ).hexdigest()

            # Comparación segura de firmas criptográficas
            if hmac.compare_digest(signature, expected_sig):
                request.session['admin_key_verified'] = True
                messages.success(request, f'¡Bienvenido de vuelta, {request.user.get_full_name() or username}! Acceso seguro concedido.')
                return redirect('panel_admin:resumen')
            else:
                messages.error(request, 'Firma digital no válida. El archivo ha sido alterado o es incorrecto.')
        except Exception as e:
            messages.error(request, 'Ocurrió un error al procesar el archivo. Asegúrate de que sea tu llave .key original.')

        return redirect('panel_admin:verificar_llave')

    return render(request, 'panel_admin/verificar_llave.html')


@staff_member_required(login_url='/auth/login/')
def solicitar_llave(request):
    """
    Envía un enlace temporal por correo electrónico SMTP seguro para descargar la llave .key.
    RESTRINGIDO: Solo el usuario 'admin' puede solicitar la llave.
    El correo se envía exclusivamente a leonardodlp88@gmail.com.
    """
    from django.contrib import messages
    from django.shortcuts import redirect
    from django.core.mail import EmailMultiAlternatives
    from django.template.loader import render_to_string
    from django.utils.html import strip_tags
    from django.utils.http import urlsafe_base64_encode
    from django.utils.encoding import force_bytes
    from django.contrib.auth.tokens import default_token_generator
    from django.conf import settings

    user = request.user

    # RESTRICCIÓN: Solo el usuario 'admin' puede solicitar la llave
    if user.username != 'admin':
        messages.error(request, 'Solo el administrador principal puede solicitar la llave de seguridad.')
        return redirect('panel_admin:verificar_llave')

    # Correo de destino fijo (no depende del email registrado en la cuenta)
    email_destino = 'leonardodlp88@gmail.com'

    # Generar UID y token seguros nativos de Django
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)

    # Construir enlace de descarga absoluta
    protocol = 'https' if request.is_secure() else 'http'
    domain = request.get_host()
    link = f"{protocol}://{domain}/panel/descargar-llave/{uid}/{token}/"

    # Enviar correo
    ctx = {
        'user': user,
        'link': link,
    }
    
    asunto = 'Paniimi Bakery — Enlace de Descarga de Llave de Seguridad 🛡'
    html_content = render_to_string('panel_admin/keyfile_email.html', ctx)
    text_content = strip_tags(html_content)

    try:
        email_msg = EmailMultiAlternatives(
            subject=asunto,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email_destino]
        )
        email_msg.attach_alternative(html_content, "text/html")
        email_msg.send(fail_silently=False)

        messages.success(request, f'Se ha enviado un enlace de descarga seguro a {email_destino}. Revisa tu bandeja de entrada.')
    except Exception as exc:
        messages.error(request, f'Error al enviar el correo: {str(exc)}')

    return redirect('panel_admin:verificar_llave')


@staff_member_required(login_url='/auth/login/')
def descargar_llave(request, uidb64, token):
    """
    Valida el token de un solo uso y descarga el archivo .key exclusivo del administrador.
    """
    from django.contrib import messages
    from django.shortcuts import redirect
    from django.contrib.auth import get_user_model
    from django.utils.http import urlsafe_base64_decode
    from django.utils.encoding import force_str
    from django.contrib.auth.tokens import default_token_generator
    from django.http import HttpResponse
    from django.conf import settings
    import hmac
    import hashlib

    User = get_user_model()

    try:
        # Decodificar el UID del usuario
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    # Validar el token y que sea el mismo usuario que la pide
    if user and user == request.user and default_token_generator.check_token(user, token):
        
        # Generar firma única HMAC-SHA256
        username = user.username
        msg = f"{username}:admin-key"
        signature = hmac.new(
            settings.SECRET_KEY.encode(),
            msg.encode(),
            hashlib.sha256
        ).hexdigest()

        # Construir contenido del archivo .key
        file_content = f"{username}:{signature}"

        # Devolver como archivo adjunto descargable (.key)
        response = HttpResponse(file_content, content_type='text/plain')
        response['Content-Disposition'] = f'attachment; filename="paniimi_key_{username}.key"'
        return response
    else:
        messages.error(request, 'El enlace de descarga ha expirado o no es válido.')
        return redirect('panel_admin:verificar_llave')


@staff_member_required(login_url='/auth/login/')
def descargar_llave_directa(request):
    """
    Descarga directa del archivo .key.
    RESTRINGIDO: Solo el usuario 'admin' puede descargar su propia llave.
    """
    from django.http import HttpResponse, HttpResponseForbidden
    from django.conf import settings
    import hmac
    import hashlib

    if request.user.username != 'admin':
        return HttpResponseForbidden('Acceso denegado.')

    user = request.user
    username = user.username

    # Generar firma única HMAC-SHA256
    msg = f"{username}:admin-key"
    signature = hmac.new(
        settings.SECRET_KEY.encode(),
        msg.encode(),
        hashlib.sha256
    ).hexdigest()

    # Construir contenido del archivo .key
    file_content = f"{username}:{signature}"

    # Devolver como archivo adjunto descargable (.key)
    response = HttpResponse(file_content, content_type='text/plain')
    response['Content-Disposition'] = f'attachment; filename="paniimi_key_{username}.key"'
    return response


@staff_member_required(login_url='/auth/login/')
def gestionar_llaves(request):
    """
    Panel de gestión de llaves de seguridad.
    RESTRINGIDO: Solo el usuario 'admin' puede ver esta página.
    Muestra todos los usuarios staff con opción de generar su llave.
    """
    from django.http import HttpResponseForbidden
    from django.contrib.auth import get_user_model

    if request.user.username != 'admin':
        return HttpResponseForbidden('Acceso denegado.')

    User = get_user_model()
    staff_users = User.objects.filter(is_staff=True).order_by('-is_superuser', 'username')

    return render(request, 'panel_admin/gestionar_llaves.html', {
        'staff_users': staff_users,
    })


@staff_member_required(login_url='/auth/login/')
def generar_llave_usuario(request, user_id):
    """
    Genera y descarga el archivo .key para un usuario staff específico.
    RESTRINGIDO: Solo el usuario 'admin' puede generar llaves.
    """
    from django.http import HttpResponse, HttpResponseForbidden
    from django.conf import settings
    from django.contrib.auth import get_user_model
    from django.shortcuts import get_object_or_404
    import hmac
    import hashlib

    if request.user.username != 'admin':
        return HttpResponseForbidden('Acceso denegado.')

    User = get_user_model()
    target_user = get_object_or_404(User, pk=user_id, is_staff=True)
    username = target_user.username

    # Generar firma única HMAC-SHA256 para el usuario objetivo
    msg = f"{username}:admin-key"
    signature = hmac.new(
        settings.SECRET_KEY.encode(),
        msg.encode(),
        hashlib.sha256
    ).hexdigest()

    # Construir contenido del archivo .key
    file_content = f"{username}:{signature}"

    # Devolver como archivo adjunto descargable (.key)
    response = HttpResponse(file_content, content_type='text/plain')
    response['Content-Disposition'] = f'attachment; filename="paniimi_key_{username}.key"'
    return response


@staff_member_required(login_url='/auth/login/')
def diagnostico_email(request):
    """
    Página de diagnóstico de correo electrónico.
    Muestra la configuración actual y permite enviar un correo de prueba.
    RESTRINGIDO: Solo el usuario 'admin'.
    """
    from django.http import HttpResponseForbidden, JsonResponse
    from django.conf import settings
    from django.core.mail import send_mail
    import traceback

    if request.user.username != 'admin':
        return HttpResponseForbidden('Acceso denegado.')

    resultado = None
    error_detalle = None

    if request.method == 'POST':
        try:
            send_mail(
                subject='🔧 Paniimi Bakery — Correo de Prueba',
                message='¡Este es un correo de prueba! Si lo recibes, el sistema de correos funciona correctamente.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[request.POST.get('email_destino', 'leonardodlp88@gmail.com')],
                fail_silently=False,
            )
            resultado = 'success'
        except Exception as exc:
            resultado = 'error'
            error_detalle = f"{type(exc).__name__}: {str(exc)}\n\n{traceback.format_exc()}"

    config = {
        'EMAIL_BACKEND': getattr(settings, 'EMAIL_BACKEND', 'No configurado'),
        'EMAIL_HOST': getattr(settings, 'EMAIL_HOST', 'No configurado'),
        'EMAIL_PORT': getattr(settings, 'EMAIL_PORT', 'No configurado'),
        'EMAIL_USE_TLS': getattr(settings, 'EMAIL_USE_TLS', 'No configurado'),
        'EMAIL_USE_SSL': getattr(settings, 'EMAIL_USE_SSL', 'No configurado'),
        'EMAIL_HOST_USER': getattr(settings, 'EMAIL_HOST_USER', 'No configurado'),
        'EMAIL_HOST_PASSWORD': '****' + getattr(settings, 'EMAIL_HOST_PASSWORD', '')[-4:] if getattr(settings, 'EMAIL_HOST_PASSWORD', '') else 'VACÍO',
        'DEFAULT_FROM_EMAIL': getattr(settings, 'DEFAULT_FROM_EMAIL', 'No configurado'),
    }

    return render(request, 'panel_admin/diagnostico_email.html', {
        'config': config,
        'resultado': resultado,
        'error_detalle': error_detalle,
    })


@staff_member_required(login_url='/auth/login/')
def poblar_catalogo_view(request):
    """
    Pobla la base de datos con los datos de prueba del script poblar_catalogo.py.
    RESTRINGIDO: Solo staff.
    """
    from django.contrib import messages
    from django.shortcuts import redirect
    import sys
    import os

    if request.user.username != 'admin':
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('Acceso denegado.')

    if request.method == 'POST':
        try:
            # Añadir directorio base al path de python si no está
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            if base_dir not in sys.path:
                sys.path.append(base_dir)
            
            # Importar la función poblar
            from poblar_catalogo import poblar
            poblar()
            messages.success(request, '¡Catálogo poblado con éxito con categorías y productos de prueba! 🐻')
        except Exception as exc:
            messages.error(request, f'Error al poblar el catálogo: {exc}')
        return redirect('panel_admin:inventario')
    return redirect('panel_admin:inventario')


@staff_member_required(login_url='/auth/login/')
def categorias(request):
    """Lista de categorías registradas en el catálogo."""
    categorias_list = Categoria.objects.all().order_by('orden', 'nombre')
    ctx = {
        'categorias': categorias_list,
        'seccion_activa': 'categorias',
    }
    return render(request, 'panel_admin/categorias.html', ctx)


@staff_member_required(login_url='/auth/login/')
def crear_categoria(request):
    """Formulario para crear una nueva categoría."""
    form = CategoriaForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        categoria = form.save()
        messages.success(request, f'Categoría "{categoria.nombre}" creada correctamente.')
        return redirect('panel_admin:categorias')

    ctx = {
        'form': form,
        'titulo': 'Nueva Categoría',
        'seccion_activa': 'categorias',
    }
    return render(request, 'panel_admin/categoria_form.html', ctx)


@staff_member_required(login_url='/auth/login/')
def editar_categoria(request, categoria_id):
    """Editar una categoría existente."""
    categoria = get_object_or_404(Categoria, pk=categoria_id)
    form = CategoriaForm(request.POST or None, instance=categoria)

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Categoría "{categoria.nombre}" actualizada.')
        return redirect('panel_admin:categorias')

    ctx = {
        'form': form,
        'categoria': categoria,
        'titulo': f'Editar Categoría: {categoria.nombre}',
        'seccion_activa': 'categorias',
    }
    return render(request, 'panel_admin/categoria_form.html', ctx)


@staff_member_required(login_url='/auth/login/')
def eliminar_categoria(request, categoria_id):
    """Eliminar una categoría y sus productos asociados."""
    categoria = get_object_or_404(Categoria, pk=categoria_id)

    if request.method == 'POST':
        nombre = categoria.nombre
        # Por on_delete=models.CASCADE, al eliminar la categoría se eliminan sus productos.
        categoria.delete()
        messages.success(request, f'Categoría "{nombre}" eliminada correctamente junto con sus productos asociados.')
        return redirect('panel_admin:categorias')

    ctx = {
        'categoria': categoria,
        'seccion_activa': 'categorias',
        'productos_afectados': categoria.productos.count(),
    }
    return render(request, 'panel_admin/categoria_confirmar_eliminar.html', ctx)


@staff_member_required(login_url='/auth/login/')
def eliminar_pedido(request, orden_id):
    """Eliminar un pedido permanentemente."""
    orden = get_object_or_404(Orden, pk=orden_id)

    if request.method == 'POST':
        pk = orden.pk
        orden.delete()
        messages.success(request, f'Pedido #{pk} eliminado correctamente.')
        return redirect('panel_admin:pedidos')

    ctx = {
        'orden': orden,
        'seccion_activa': 'pedidos',
    }
    return render(request, 'panel_admin/orden_confirmar_eliminar.html', ctx)

