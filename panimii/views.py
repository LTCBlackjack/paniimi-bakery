import json
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.mail import send_mail
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from catalogo.models import Orden, OrdenItem, Producto
from .forms import ContactoForm, DireccionEntregaForm, RegistroForm

logger = logging.getLogger(__name__)


def home(request):
    """
    Vista de la página de inicio.
    Consulta productos destacados y disponibles para mostrarlos
    en la sección de ofertas especiales al inicio.
    Si no hay productos destacados, muestra los 3 productos disponibles más recientes como fallback.
    """
    ofertas = Producto.objects.filter(destacado=True, disponible=True)[:3]
    if not ofertas.exists():
        ofertas = Producto.objects.filter(disponible=True)[:3]

    ctx = {
        'ofertas': ofertas,
    }
    return render(request, 'home.html', ctx)


# ════════════════════════════════════════════════════════════════════════
# LOGIN PERSONALIZADO
# Redirige a /panel/ si el usuario es staff o superusuario,
# y al inicio (/) si es cliente normal.
# ════════════════════════════════════════════════════════════════════════

class SmartLoginView(LoginView):
    """
    Extiende LoginView para detectar el rol del usuario tras el login
    y redirigirlo al destino correcto:
    - Staff / Superusuario  →  /panel/
    - Cliente normal        →  / (o ?next= si existe)
    """
    template_name = 'login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        # Si hay un ?next= explícito en la URL, respetarlo siempre
        next_url = self.get_redirect_url()
        if next_url:
            return next_url
        # Sin ?next=: redirigir según rol
        if self.request.user.is_staff or self.request.user.is_superuser:
            return '/panel/'
        return '/'


def contacto(request):
    """
    GET  → formulario vacío.
    POST → envía correo SMTP y redirige (PRG).
    """
    if request.method == 'POST':
        form = ContactoForm(request.POST)
        if form.is_valid():
            nombre  = form.cleaned_data['nombre']
            email   = form.cleaned_data['email']
            mensaje = form.cleaned_data['mensaje']

            asunto = f'[Paniimi Bakery] Nuevo mensaje de {nombre}'
            cuerpo = (
                f'Nombre:  {nombre}\n'
                f'Correo:  {email}\n'
                f'\n'
                f'Mensaje:\n{mensaje}\n'
                f'\n'
                f'--- Enviado desde el formulario de contacto de Paniimi Bakery ---'
            )

            try:
                send_mail(
                    subject        = asunto,
                    message        = cuerpo,
                    from_email     = settings.DEFAULT_FROM_EMAIL,
                    recipient_list = [settings.EMAIL_DESTINATARIO],
                    fail_silently  = False,
                )
                messages.success(request, '¡Mensaje enviado! Te contestaremos pronto. 🐻')
            except Exception as exc:
                logger.error('Error al enviar correo de contacto: %s', exc)
                messages.error(
                    request,
                    'Hubo un problema al enviar tu mensaje. '
                    'Intenta de nuevo o escríbenos directamente a contacto@paniimi.com.',
                )

            return redirect('contacto')
    else:
        form = ContactoForm()

    return render(request, 'contacto.html', {'form': form})


def registro(request):
    """
    Vista de registro público con activación por correo.

    GET  → formulario vacío.
    POST → crea el usuario inactivo, le envía el correo de activación y
           redirige a la pantalla de activación pendiente.
    """
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False  # Inactivo por defecto hasta verificar correo
            user.save()

            # Enviar correo de activación
            from django.contrib.auth.tokens import default_token_generator
            from django.utils.http import urlsafe_base64_encode
            from django.utils.encoding import force_bytes
            from django.template.loader import render_to_string
            from django.core.mail import send_mail

            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)

            protocol = 'https' if request.is_secure() else 'http'
            domain = request.get_host()

            asunto = render_to_string('activation_subject.txt').strip()
            cuerpo = render_to_string('activation_email.html', {
                'user': user,
                'uid': uid,
                'token': token,
                'protocol': protocol,
                'domain': domain,
            })

            try:
                send_mail(
                    subject=asunto,
                    message="",
                    html_message=cuerpo,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False,
                )
                messages.success(request, f'¡Cuenta creada, {user.username}! Revisa tu correo para activarla. 🐻')
            except Exception as exc:
                logger.error('Error al enviar correo de activación: %s', exc)
                messages.warning(
                    request,
                    'Se creó tu cuenta pero no pudimos enviarte el correo de activación. '
                    'Por favor contáctanos para activarla de inmediato.',
                )

            return redirect('registro_pendiente')
    else:
        form = RegistroForm()

    return render(request, 'registro.html', {'form': form})


def activar_cuenta(request, uidb64, token):
    """
    Activa una cuenta de usuario inactiva a través del enlace de activación seguro enviado por correo.
    """
    from django.contrib.auth import get_user_model
    from django.contrib.auth.tokens import default_token_generator
    from django.utils.http import urlsafe_base64_decode
    from django.utils.encoding import force_str

    User = get_user_model()
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        return render(request, 'activation_success.html', {'exito': True})
    else:
        return render(request, 'activation_success.html', {'exito': False})


# ════════════════════════════════════════════════════════════════════════
# CARRITO DE COMPRAS  (sesión — sin modelo por ahora)
# Estructura de session['carrito']:
#   { 'producto_id': { nombre, precio, cantidad, imagen } }
# ════════════════════════════════════════════════════════════════════════

def ver_carrito(request):
    """
    Construye la lista de ítems del carrito desde la sesión
    y calcula totales para pasarlos al template.
    """
    from decimal import Decimal, InvalidOperation

    carrito_session = request.session.get('carrito', {})
    items  = []
    total  = Decimal('0.00')

    for producto_id, datos in carrito_session.items():
        try:
            precio   = Decimal(str(datos['precio']))
            cantidad = int(datos['cantidad'])
            subtotal = precio * cantidad
            items.append({
                'id':       producto_id,
                'nombre':   datos['nombre'],
                'precio':   precio,
                'cantidad': cantidad,
                'imagen':   datos.get('imagen', ''),
                'subtotal': subtotal,
            })
            total += subtotal
        except (InvalidOperation, KeyError, ValueError):
            continue  # omite entradas corruptas

    form_direccion = DireccionEntregaForm()
    
    # Obtener direcciones guardadas de PostgreSQL
    direcciones_guardadas = []
    if request.user.is_authenticated:
        from catalogo.models import DireccionEnvio
        direcciones_guardadas = DireccionEnvio.objects.filter(cliente=request.user)

    return render(request, 'carrito.html', {
        'items':            items,
        'total':            total,
        'stripe_public_key': settings.STRIPE_PUBLIC_KEY,
        'form_direccion':   form_direccion,
        'direcciones_guardadas': direcciones_guardadas,
    })


def agregar_al_carrito(request, producto_id):
    """
    POST: añade 1 unidad del producto al carrito de sesión.
    Redirige a la página anterior (Referer) o al catálogo.
    """
    from catalogo.models import Producto as ProductoModel
    if request.method != 'POST':
        return redirect('catalogo:lista')

    try:
        producto = ProductoModel.objects.get(id=producto_id, disponible=True)
    except ProductoModel.DoesNotExist:
        messages.error(request, 'Producto no disponible.')
        return redirect('catalogo:lista')

    carrito   = request.session.get('carrito', {})
    key       = str(producto_id)

    if key in carrito:
        carrito[key]['cantidad'] += 1
    else:
        carrito[key] = {
            'nombre':   producto.nombre,
            'precio':   str(producto.precio),
            'cantidad': 1,
            'imagen':   producto.imagen.url if producto.imagen else '',
        }

    request.session['carrito']  = carrito
    request.session.modified    = True

    messages.success(request, f'"{producto.nombre}" añadido al carrito.')
    return redirect(request.META.get('HTTP_REFERER', 'catalogo:lista'))


def actualizar_carrito(request, producto_id):
    """
    POST: incrementa (+), decrementa (-) o elimina un ítem del carrito.
    Requiere campo 'accion' = 'mas' | 'menos' | 'eliminar'.
    """
    if request.method != 'POST':
        return redirect('ver_carrito')

    accion  = request.POST.get('accion', '')
    carrito = request.session.get('carrito', {})
    key     = str(producto_id)

    if key in carrito:
        if accion == 'mas':
            carrito[key]['cantidad'] += 1
        elif accion == 'menos':
            if carrito[key]['cantidad'] > 1:
                carrito[key]['cantidad'] -= 1
            else:
                del carrito[key]
        elif accion == 'eliminar':
            del carrito[key]

    request.session['carrito'] = carrito
    request.session.modified   = True
    return redirect('ver_carrito')


def enviar_correo_confirmacion_pedido(orden, request):
    """
    Envía un correo HTML de confirmación de pedido al cliente con el comprobante de su compra.
    """
    from django.template.loader import render_to_string
    from django.core.mail import send_mail
    from django.conf import settings

    protocol = 'https' if request.is_secure() else 'http'
    domain = request.get_host()

    asunto = render_to_string('orden_confirmacion_subject.txt', {'orden': orden}).strip()
    cuerpo = render_to_string('orden_confirmacion_email.html', {
        'orden': orden,
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
        logger.error('Error al enviar correo de confirmación de pedido #%s: %s', orden.pk, exc)


# ════════════════════════════════════════════════════════════════════════
# CHECKOUT — Crear Orden + PaymentIntent Stripe
# POST JSON: { payment_method_id, direccion: {...} }
# ════════════════════════════════════════════════════════════════════════

@login_required
@require_POST
def crear_orden_checkout(request):
    """
    Recibe el PaymentMethod de Stripe y los datos de dirección,
    crea un PaymentIntent, registra la Orden en PostgreSQL y
    confirma el pago.

    Responde con JSON:
      { ok: true, orden_id, client_secret }  → éxito
      { ok: false, error }                   → fallo
    """
    import stripe
    from decimal import Decimal

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'Datos inválidos.'}, status=400)

    payment_method_id = data.get('payment_method_id', '').strip()
    direccion_data    = data.get('direccion', {})

    # ── Validar dirección ────────────────────────────────────────
    form = DireccionEntregaForm(direccion_data)
    if not form.is_valid():
        errores = {k: v[0] for k, v in form.errors.items()}
        return JsonResponse({'ok': False, 'error': 'Verifica los datos de entrega.', 'campos': errores}, status=422)

    # ── Reconstruir carrito desde sesión ─────────────────────────
    carrito_session = request.session.get('carrito', {})
    if not carrito_session:
        return JsonResponse({'ok': False, 'error': 'Tu carrito está vacío.'}, status=400)

    items_carrito = []
    total         = Decimal('0.00')
    for producto_id, datos in carrito_session.items():
        try:
            precio   = Decimal(str(datos['precio']))
            cantidad = int(datos['cantidad'])
            items_carrito.append({
                'producto_id':    producto_id,
                'nombre':         datos['nombre'],
                'precio':         precio,
                'cantidad':       cantidad,
            })
            total += precio * cantidad
        except (KeyError, ValueError):
            continue

    if not items_carrito or total <= 0:
        return JsonResponse({'ok': False, 'error': 'Carrito inválido.'}, status=400)

    # ── Stripe: crear y confirmar PaymentIntent ───────────────────
    stripe.api_key = settings.STRIPE_SECRET_KEY
    monto_centavos = int(total * 100)  # Stripe trabaja en centavos

    try:
        intent = stripe.PaymentIntent.create(
            amount              = monto_centavos,
            currency            = 'mxn',
            payment_method      = payment_method_id,
            confirmation_method = 'manual',
            confirm             = True,
            return_url          = request.build_absolute_uri('/carrito/'),
            metadata            = {
                'cliente_id':   request.user.id,
                'cliente_email': request.user.email,
            },
        )
    except stripe.error.CardError as e:
        return JsonResponse({'ok': False, 'error': e.user_message}, status=402)
    except stripe.error.StripeError as e:
        logger.error('Stripe error en checkout: %s', e)
        return JsonResponse({'ok': False, 'error': 'Error al procesar el pago. Intenta de nuevo.'}, status=502)

    # ── Crear Orden en PostgreSQL ─────────────────────────────────
    cd = form.cleaned_data
    orden = Orden.objects.create(
        cliente                  = request.user,
        email_cliente            = request.user.email,
        total                    = total,
        stripe_payment_intent_id = intent.id,
        metodo_pago              = 'card',
        # Dirección
        telefono      = cd['telefono'],
        calle         = cd['calle'],
        colonia       = cd['colonia'],
        ciudad        = cd.get('ciudad', 'Mérida'),
        estado_mx     = cd.get('estado_mx', 'Yucatán'),
        codigo_postal = cd['codigo_postal'],
        referencias   = cd.get('referencias', ''),
        # Estado según resultado de Stripe
        estado = Orden.Estado.PAGADA if intent.status == 'succeeded' else Orden.Estado.PENDIENTE,
    )

    # ── Autoguardar dirección de envío si se solicita ──────────────
    if data.get('guardar_direccion', False):
        from catalogo.models import DireccionEnvio
        ya_existe = DireccionEnvio.objects.filter(
            cliente=request.user,
            telefono=cd['telefono'],
            calle=cd['calle'],
            colonia=cd['colonia'],
            codigo_postal=cd['codigo_postal'],
            ciudad=cd.get('ciudad', 'Mérida'),
            estado_mx=cd.get('estado_mx', 'Yucatán'),
        ).exists()
        
        if not ya_existe:
            alias_nuevo = f"Dirección de Compra #{request.user.direcciones.count() + 1}"
            DireccionEnvio.objects.create(
                cliente=request.user,
                alias=alias_nuevo,
                telefono=cd['telefono'],
                calle=cd['calle'],
                colonia=cd['colonia'],
                codigo_postal=cd['codigo_postal'],
                ciudad=cd.get('ciudad', 'Mérida'),
                estado_mx=cd.get('estado_mx', 'Yucatán'),
                referencias=cd.get('referencias', ''),
                predetermina=request.user.direcciones.count() == 0
            )

    # Crear ítems de la orden
    for item in items_carrito:
        try:
            producto = Producto.objects.get(pk=item['producto_id'])
        except Producto.DoesNotExist:
            producto = None
        OrdenItem.objects.create(
            orden           = orden,
            producto        = producto,
            nombre_producto = item['nombre'],
            precio_unitario = item['precio'],
            cantidad        = item['cantidad'],
        )

    # ── Vaciar el carrito ─────────────────────────────────────────
    request.session['carrito'] = {}
    request.session.modified   = True

    # ── Respuesta según estado del intent ─────────────────────────
    if intent.status == 'succeeded':
        enviar_correo_confirmacion_pedido(orden, request)
        return JsonResponse({'ok': True, 'orden_id': orden.pk})
    elif intent.status == 'requires_action':
        # Requiere autenticación 3D Secure
        return JsonResponse({
            'ok':           True,
            'requires_action': True,
            'client_secret':   intent.client_secret,
            'orden_id':        orden.pk,
        })
    else:
        return JsonResponse({'ok': False, 'error': f'Estado inesperado: {intent.status}'}, status=502)



@login_required
def dashboard(request):
    """
    Panel principal del usuario autenticado.

    Muestra información de perfil, puntos de lealtad reales basados en sus compras,
    historial de pedidos dinámico obtenido de PostgreSQL y productos sugeridos.
    """
    # 1. Obtener órdenes reales del usuario en PostgreSQL
    pedidos_qs = (
        Orden.objects
        .filter(cliente=request.user)
        .prefetch_related('items')
        .order_by('-creado')
    )

    pedidos = []
    for o in pedidos_qs:
        # Generar una descripción amigable basada en los ítems
        items_desc = ", ".join([f"{item.cantidad}x {item.nombre_producto}" for item in o.items.all()])
        if not items_desc:
            items_desc = "Pedido de panadería"

        pedidos.append({
            'numero':      o.codigo_pedido,
            'fecha':       o.creado,
            'descripcion': items_desc,
            'total':       o.total,
            'estatus':     o.get_estado_display(),
        })

    # 2. Calcular puntos de lealtad (1 punto por pedido pagado, ciclo de 6 puntos)
    total_pagados = pedidos_qs.filter(estado=Orden.Estado.PAGADA).count()
    puntos_lealtad = 6 if (total_pagados > 0 and total_pagados % 6 == 0) else (total_pagados % 6)

    # 3. Productos destacados o los 4 más recientes para "Sugeridos para ti"
    sugeridos = (
        Producto.objects
        .filter(disponible=True)
        .select_related('categoria')
        .order_by('-destacado', '-creado')[:4]
    )

    # 4. Obtener direcciones guardadas de PostgreSQL
    from catalogo.models import DireccionEnvio
    from .forms import DireccionEnvioForm
    direcciones = DireccionEnvio.objects.filter(cliente=request.user)
    form_direccion = DireccionEnvioForm()

    ctx = {
        'sugeridos':      sugeridos,
        'puntos_lealtad': puntos_lealtad,
        'pedidos':        pedidos,
        'direcciones':    direcciones,
        'form_direccion': form_direccion,
    }
    return render(request, 'dashboard.html', ctx)


@login_required
def orden_exito(request, pk):
    """
    Pantalla dedicada para confirmar la orden recibida y realizar
    el seguimiento dinámico del estado de logística del pedido.
    """
    from django.shortcuts import get_object_or_404
    from django.http import Http404

    orden = get_object_or_404(Orden, pk=pk)

    # Seguridad: solo el cliente que hizo el pedido o staff
    if orden.cliente != request.user and not request.user.is_staff:
        raise Http404("No tienes permisos para ver esta orden.")

    # Mapeo de estados para la línea de tiempo dinámica
    # Estados de Orden.Estado: pendiente, pagada, en_proceso, enviada, entregada, cancelada
    estado = orden.estado

    pasos = [
        {
            'id': 'recibida',
            'nombre': 'Orden Recibida',
            'descripcion': 'Tu orden ha sido registrada con éxito.',
            'completado': True,
            'activo': estado != 'cancelada',
        },
        {
            'id': 'preparando',
            'nombre': 'En Preparación',
            'descripcion': 'Nuestros reposteros están horneando tus panes.',
            'completado': estado in ['pagada', 'en_proceso', 'enviada', 'entregada'],
            'activo': estado != 'cancelada' and estado in ['pagada', 'en_proceso', 'enviada', 'entregada'],
        },
        {
            'id': 'enviada',
            'nombre': 'En Camino',
            'descripcion': 'Tu orden va rumbo a tu dirección de envío.',
            'completado': estado in ['enviada', 'entregada'],
            'activo': estado != 'cancelada' and estado in ['enviada', 'entregada'],
        },
        {
            'id': 'entregada',
            'nombre': 'Entregado',
            'descripcion': '¡Orden entregada! Disfruta de la dulzura.',
            'completado': estado == 'entregada',
            'activo': estado == 'entregada',
        }
    ]

    ctx = {
        'orden': orden,
        'pasos': pasos,
    }
    return render(request, 'orden_exito.html', ctx)


@login_required
@require_POST
def guardar_direccion_ajax(request):
    """
    Agrega una nueva dirección o edita una existente.
    Recibe JSON y responde JSON.
    """
    from catalogo.models import DireccionEnvio
    from .forms import DireccionEnvioForm

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'Datos inválidos.'}, status=400)

    direccion_id = data.get('id')
    instancia = None

    if direccion_id:
        # Modo Edición: verificar propiedad
        instancia = get_object_or_404(DireccionEnvio, pk=direccion_id, cliente=request.user)

    form = DireccionEnvioForm(data, instance=instancia)
    if form.is_valid():
        direccion = form.save(commit=False)
        direccion.cliente = request.user
        
        # Si es la primera dirección, forzar que sea predeterminada
        if request.user.direcciones.count() == 0:
            direccion.predetermina = True
            
        direccion.save()
        return JsonResponse({
            'ok': True,
            'direccion': {
                'id':            direccion.pk,
                'alias':         direccion.alias,
                'telefono':      direccion.telefono,
                'calle':         direccion.calle,
                'colonia':       direccion.colonia,
                'ciudad':        direccion.ciudad,
                'estado_mx':     direccion.estado_mx,
                'codigo_postal': direccion.codigo_postal,
                'referencias':   direccion.referencias,
                'predetermina':  direccion.predetermina,
            }
        })
    else:
        errores = {k: v[0] for k, v in form.errors.items()}
        return JsonResponse({'ok': False, 'error': 'Verifica los campos ingresados.', 'campos': errores}, status=422)


@login_required
@require_POST
def eliminar_direccion_ajax(request):
    """
    Elimina una dirección de envío guardada.
    """
    from catalogo.models import DireccionEnvio
    try:
        data = json.loads(request.body)
        direccion_id = data.get('id')
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'Datos inválidos.'}, status=400)

    direccion = get_object_or_404(DireccionEnvio, pk=direccion_id, cliente=request.user)
    
    # Si la eliminada es predeterminada, hacer que otra sea favorita si existen más
    era_predeterminada = direccion.predetermina
    direccion.delete()

    if era_predeterminada:
        siguiente = request.user.direcciones.first()
        if siguiente:
            siguiente.predetermina = True
            siguiente.save()

    return JsonResponse({'ok': True})


@login_required
@require_POST
def establecer_predeterminada_ajax(request):
    """
    Establece una dirección de envío como predeterminada/favorita.
    """
    from catalogo.models import DireccionEnvio
    try:
        data = json.loads(request.body)
        direccion_id = data.get('id')
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'Datos inválidos.'}, status=400)

    direccion = get_object_or_404(DireccionEnvio, pk=direccion_id, cliente=request.user)
    direccion.predetermina = True
    direccion.save()  # Nuestro modelo save() apaga las otras automáticamente

    return JsonResponse({'ok': True})


