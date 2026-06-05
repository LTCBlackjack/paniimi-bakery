import os
from io import BytesIO

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import models
from django.utils.text import slugify
from PIL import Image


class Categoria(models.Model):
    """Modelo para las categorías del catálogo de la panadería."""

    nombre = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    descripcion = models.TextField(blank=True)
    activa = models.BooleanField(default=True)
    orden = models.PositiveIntegerField(default=0, help_text='Orden de aparición en el catálogo')
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Categoría'
        verbose_name_plural = 'Categorías'
        ordering = ['orden', 'nombre']

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nombre)
        super().save(*args, **kwargs)


class Producto(models.Model):
    """
    Modelo para los productos de la panadería.

    Las imágenes subidas se comprimen automáticamente y se convierten
    a formato WebP para optimizar el almacenamiento del servidor (1 GB).
    """

    # ── Configuración de compresión ──────────────────────────────
    WEBP_QUALITY = 80           # Calidad WebP (0-100)
    MAX_IMAGE_SIZE = (1200, 1200)  # Dimensión máxima en píxeles

    # ── Campos del modelo ──────────────────────────────────────────
    nombre = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    codigo = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        editable=False,
        verbose_name='Código de producto',
        help_text='Generado automáticamente. Formato: G-ddmmaahhN',
    )
    descripcion = models.TextField(blank=True)
    precio = models.DecimalField(max_digits=8, decimal_places=2)
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.CASCADE,
        related_name='productos',
    )
    imagen = models.ImageField(
        upload_to='productos/',
        blank=True,
        null=True,
        help_text='La imagen se comprimirá y convertirá a WebP automáticamente.',
    )
    disponible = models.BooleanField(default=True)
    destacado = models.BooleanField(
        default=False,
        help_text='Mostrar en la sección de productos destacados.',
    )
    stock = models.PositiveIntegerField(
        default=0,
        help_text='Número de unidades disponibles en inventario.',
    )
    precio_grande = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Precio Grande (Opcional)',
        help_text='Precio para el tamaño grande del producto. Dejar vacío si solo hay un tamaño.',
    )
    stock_grande = models.PositiveIntegerField(
        default=0,
        verbose_name='Stock Grande (Opcional)',
        help_text='Número de unidades de tamaño grande disponibles en inventario.',
    )
    descuento_porcentaje = models.PositiveIntegerField(
        default=0,
        verbose_name='Descuento (%)',
        help_text='Porcentaje de descuento para el producto en ofertas especiales (ej. 15 para 15% OFF). Deja en 0 para sin descuento.',
    )
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'
        ordering = ['-destacado', '-creado']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['categoria', 'disponible']),
        ]

    def __str__(self):
        return self.nombre

    @property
    def precio_descuento(self):
        """Devuelve el precio del producto con su descuento correspondiente, o el precio normal si no tiene."""
        if self.descuento_porcentaje > 0:
            from decimal import Decimal
            factor = Decimal(1 - self.descuento_porcentaje / 100.0)
            return (self.precio * factor).quantize(Decimal('0.01'))
        return self.precio

    # ── Compresión automática de imágenes ────────────────────────
    def _compress_image(self):
        """
        Comprime la imagen subida y la convierte a formato WebP.

        - Redimensiona si excede MAX_IMAGE_SIZE (manteniendo proporción).
        - Convierte cualquier formato (PNG, JPEG, etc.) a WebP.
        - Aplica la calidad definida en WEBP_QUALITY.
        """
        if not self.imagen:
            return

        img = Image.open(self.imagen)

        # Convertir modos incompatibles con WebP (ej. CMYK, P, LA)
        if img.mode in ('RGBA', 'LA'):
            # Conservar transparencia
            pass
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        # Redimensionar si excede las dimensiones máximas
        img.thumbnail(self.MAX_IMAGE_SIZE, Image.LANCZOS)

        # Guardar en buffer como WebP
        buffer = BytesIO()
        img.save(buffer, format='WEBP', quality=self.WEBP_QUALITY, optimize=True)
        buffer.seek(0)

        # Generar nuevo nombre con extensión .webp
        nombre_original = os.path.splitext(os.path.basename(self.imagen.name))[0]
        nuevo_nombre = f'{nombre_original}.webp'

        # Reemplazar el archivo de imagen
        self.imagen.save(nuevo_nombre, ContentFile(buffer.read()), save=False)

    def _generar_slug_unico(self):
        """
        Genera un slug único basado en el nombre del producto.
        Si 'galleta-choco' ya existe, intenta 'galleta-choco-2',
        'galleta-choco-3', etc. hasta encontrar uno libre.
        """
        base = slugify(self.nombre)
        slug = base
        n = 2
        # Excluir el propio objeto al editar (si ya tiene PK)
        qs = Producto.objects.filter(slug=slug)
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        while qs.exists():
            slug = f'{base}-{n}'
            n += 1
            qs = Producto.objects.filter(slug=slug)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
        return slug

    def _generar_codigo(self):
        """
        Genera un código único de producto con el formato G-ddmmaahhN.

        Componentes:
          G     → Galleta (tipo de producto)
          dd    → Día con cero a la izquierda  (01-31)
          mm    → Mes con cero a la izquierda  (01-12)
          aa    → Año de 2 dígitos            (26 para 2026)
          hh    → Hora en formato 24 h          (00-23)
          N     → Número consecutivo para esa hora (1, 2, 3 …)

        Ejemplo: G-0505261401  → primer producto del 5 May 2026 a las 14 h.
        """
        from django.utils import timezone
        now    = timezone.localtime()
        prefix = f"G-{now.strftime('%d%m%y%H')}"

        # Contar productos con el mismo prefijo para obtener el consecutivo
        n      = Producto.objects.filter(codigo__startswith=prefix).count() + 1
        codigo = f"{prefix}{n}"

        # Garantizar unicidad ante creaciones simultáneas
        while Producto.objects.filter(codigo=codigo).exists():
            n += 1
            codigo = f"{prefix}{n}"

        return codigo

    def save(self, *args, **kwargs):
        # Generar slug único (maneja colisiones automáticamente)
        if not self.slug:
            self.slug = self._generar_slug_unico()
        # Generar código de producto únicamente al crear (nunca al editar)
        if not self.codigo:
            self.codigo = self._generar_codigo()

        # Comprimir imagen solo si es nueva o fue actualizada
        if self.pk:
            try:
                viejo = Producto.objects.get(pk=self.pk)
                imagen_cambio = viejo.imagen != self.imagen
            except Producto.DoesNotExist:
                imagen_cambio = True
        else:
            imagen_cambio = True

        # Primero guardamos para obtener el PK y la ruta del archivo
        super().save(*args, **kwargs)

        # Comprimir y re-guardar solo si la imagen cambió
        if imagen_cambio and self.imagen:
            self._compress_image()
            # Guardar de nuevo para persistir la imagen comprimida
            # Usamos update_fields para evitar recursión infinita
            super().save(update_fields=['imagen'])



# ════════════════════════════════════════════════════════════════════════
# ÓRDENES DE COMPRA
# ════════════════════════════════════════════════════════════════════════

class Orden(models.Model):
    """Representa una orden de compra realizada por un cliente."""

    class Estado(models.TextChoices):
        PENDIENTE  = 'pendiente',  'Pendiente'
        PAGADA     = 'pagada',     'Pagada'
        EN_PROCESO = 'en_proceso', 'En proceso'
        ENVIADA    = 'enviada',    'Enviada'
        ENTREGADA  = 'entregada',  'Entregada'
        CANCELADA  = 'cancelada',  'Cancelada'

    cliente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ordenes',
    )
    email_cliente = models.EmailField(blank=True)
    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.PENDIENTE,
    )
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    costo_envio = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Costo de envío')
    notas = models.TextField(blank=True)

    # ── Dirección de entrega ─────────────────────────────────────
    telefono      = models.CharField(max_length=20, blank=True, verbose_name='Teléfono de contacto')
    calle         = models.CharField(max_length=200, blank=True, verbose_name='Calle y número')
    colonia       = models.CharField(max_length=100, blank=True, verbose_name='Colonia')
    ciudad        = models.CharField(max_length=100, blank=True, default='Mérida', verbose_name='Ciudad')
    estado_mx     = models.CharField(max_length=50,  blank=True, default='Yucatán', verbose_name='Estado')
    codigo_postal = models.CharField(max_length=10,  blank=True, verbose_name='Código postal')
    referencias   = models.TextField(blank=True, verbose_name='Referencias de entrega',
                                     help_text='Ej: casa azul, junto al OXXO, portón negro')

    # ── Stripe ───────────────────────────────────────────────────
    stripe_payment_intent_id = models.CharField(
        max_length=200, blank=True, db_index=True,
        verbose_name='Stripe PaymentIntent ID',
    )
    metodo_pago = models.CharField(
        max_length=50, blank=True, default='card',
        verbose_name='Método de pago',
    )

    creado    = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Orden'
        verbose_name_plural = 'Órdenes'
        ordering = ['-creado']

    def __str__(self):
        cliente_str = self.cliente.username if self.cliente else self.email_cliente or 'Anónimo'
        return f'Orden #{self.pk} — {cliente_str}'
        
    @property
    def subtotal(self):
        return self.total - self.costo_envio

    def calcular_total(self):
        """Recalcula el total sumando todos los ítems y el costo de envío."""
        self.total = sum(item.subtotal() for item in self.items.all()) + self.costo_envio
        self.save(update_fields=['total'])

    @property
    def direccion_completa(self):
        """Devuelve la dirección formateada en una línea."""
        partes = [p for p in [self.calle, self.colonia, self.ciudad, self.estado_mx, self.codigo_postal] if p]
        return ', '.join(partes)

    @property
    def codigo_pedido(self):
        """
        Genera el código del pedido con la sintaxis:
        Número de pedido + Día (ddmmaaaa) + Hora (hhmmss) + Número de artículos
        """
        if not self.pk or not self.creado:
            return "NUEVO"
        from django.utils import timezone
        local_dt = timezone.localtime(self.creado)
        dia_str = local_dt.strftime('%d%m%Y')
        hora_str = local_dt.strftime('%H%M%S')
        total_articulos = sum(item.cantidad for item in self.items.all())
        return f"{self.pk}{dia_str}{hora_str}{total_articulos}"




class OrdenItem(models.Model):
    """Línea individual dentro de una Orden."""

    orden    = models.ForeignKey(Orden, on_delete=models.CASCADE, related_name='items')
    producto = models.ForeignKey(
        Producto,
        on_delete=models.SET_NULL,
        null=True,
        related_name='orden_items',
    )
    nombre_producto = models.CharField(max_length=200)  # snapshot del nombre
    precio_unitario = models.DecimalField(max_digits=8, decimal_places=2)
    cantidad        = models.PositiveIntegerField(default=1)
    tamano          = models.CharField(
        max_length=50,
        blank=True,
        default='',
        verbose_name='Tamaño',
    )

    class Meta:
        verbose_name = 'Ítem de Orden'
        verbose_name_plural = 'Ítems de Orden'

    def __str__(self):
        return f'{self.cantidad}× {self.nombre_producto}'

    def subtotal(self):
        return self.precio_unitario * self.cantidad


class DireccionEnvio(models.Model):
    """Direcciones de entrega guardadas por los clientes."""

    cliente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='direcciones',
    )
    alias = models.CharField(max_length=50, default='Mi Casa', verbose_name='Alias de la dirección')
    telefono = models.CharField(max_length=20, verbose_name='Teléfono de contacto')
    calle = models.CharField(max_length=200, verbose_name='Calle y número')
    colonia = models.CharField(max_length=100, verbose_name='Colonia')
    ciudad = models.CharField(max_length=100, default='Mérida', verbose_name='Ciudad')
    estado_mx = models.CharField(max_length=50, default='Yucatán', verbose_name='Estado')
    codigo_postal = models.CharField(max_length=10, verbose_name='Código postal')
    referencias = models.TextField(blank=True, verbose_name='Referencias de entrega')
    predetermina = models.BooleanField(default=False, verbose_name='Dirección predeterminada')

    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Dirección de Envío'
        verbose_name_plural = 'Direcciones de Envío'
        ordering = ['-predetermina', '-creado']

    def __str__(self):
        return f'{self.alias} — {self.calle}'

    def save(self, *args, **kwargs):
        # Garantizar que solo una dirección sea la predeterminada
        if self.predetermina:
            DireccionEnvio.objects.filter(cliente=self.cliente).exclude(pk=self.pk).update(predetermina=False)
        super().save(*args, **kwargs)


class ConfiguracionTemporada(models.Model):
    """Configuración global de la temporada/estación activa para personalizar el diseño del sitio (Singleton)."""

    class Temporadas(models.TextChoices):
        ORIGINAL = 'original', 'Original'
        PRIMAVERA = 'primavera', 'Primavera'
        VERANO = 'verano', 'Verano'
        OTONO = 'otono', 'Otoño'
        INVIERNO = 'invierno', 'Invierno'

    temporada = models.CharField(
        max_length=20,
        choices=Temporadas.choices,
        default=Temporadas.ORIGINAL,
        verbose_name='Temporada activa'
    )
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Configuración de Temporada'
        verbose_name_plural = 'Configuraciones de Temporada'

    def __str__(self):
        return f"Temporada: {self.get_temporada_display()}"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_activa(cls):
        obj, created = cls.objects.get_or_create(pk=1, defaults={'temporada': cls.Temporadas.ORIGINAL})
        return obj.temporada


