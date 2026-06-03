"""
Formularios del Panel de Administración — Gestión de Clientes.
"""
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

User = get_user_model()


class EditarClienteForm(forms.ModelForm):
    """
    Formulario para editar un usuario existente.
    No toca la contraseña — eso se maneja por separado si hace falta.
    Solo superusuarios pueden activar is_staff / is_superuser.
    """

    class Meta:
        model  = User
        fields = [
            'username', 'first_name', 'last_name',
            'email', 'is_active', 'is_staff', 'is_superuser',
        ]
        labels = {
            'username':     'Usuario',
            'first_name':   'Nombre',
            'last_name':    'Apellido',
            'email':        'Correo electrónico',
            'is_active':    'Cuenta activa',
            'is_staff':     'Acceso al panel (staff)',
            'is_superuser': 'Superusuario',
        }
        help_texts = {
            'is_staff':     'Permite acceder al Panel de Administración.',
            'is_superuser': 'Todos los permisos sin restricción.',
            'username':     '',
        }
        widgets = {
            'username':   forms.TextInput(attrs={'autocomplete': 'off'}),
            'first_name': forms.TextInput(),
            'last_name':  forms.TextInput(),
            'email':      forms.EmailInput(),
        }

    def __init__(self, *args, **kwargs):
        requesting_user = kwargs.pop('requesting_user', None)
        super().__init__(*args, **kwargs)
        if not (requesting_user and requesting_user.is_superuser):
            if 'is_staff' in self.fields:
                self.fields['is_staff'].disabled = True
            if 'is_superuser' in self.fields:
                self.fields['is_superuser'].disabled = True

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip()
        qs = User.objects.filter(email=email).exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError('Ya existe un usuario con este correo.')
        return email


class CrearClienteForm(forms.ModelForm):
    """
    Formulario para crear un nuevo usuario desde el panel admin.
    Incluye campos de contraseña con confirmación.
    """
    password1 = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        help_text='Mínimo 8 caracteres.',
    )
    password2 = forms.CharField(
        label='Confirmar contraseña',
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
    )

    class Meta:
        model  = User
        fields = [
            'username', 'first_name', 'last_name',
            'email', 'is_active', 'is_staff', 'is_superuser',
        ]
        labels = {
            'username':     'Usuario',
            'first_name':   'Nombre',
            'last_name':    'Apellido',
            'email':        'Correo electrónico',
            'is_active':    'Cuenta activa',
            'is_staff':     'Acceso al panel (staff)',
            'is_superuser': 'Superusuario',
        }
        help_texts = {
            'username':     '',
            'is_staff':     'Permite acceder al Panel de Administración.',
            'is_superuser': 'Todos los permisos sin restricción.',
        }
        widgets = {
            'username':   forms.TextInput(attrs={'autocomplete': 'off'}),
            'first_name': forms.TextInput(),
            'last_name':  forms.TextInput(),
            'email':      forms.EmailInput(),
        }

    def __init__(self, *args, **kwargs):
        requesting_user = kwargs.pop('requesting_user', None)
        super().__init__(*args, **kwargs)
        if not (requesting_user and requesting_user.is_superuser):
            if 'is_staff' in self.fields:
                self.fields['is_staff'].disabled = True
                self.fields['is_staff'].initial = False
            if 'is_superuser' in self.fields:
                self.fields['is_superuser'].disabled = True
                self.fields['is_superuser'].initial = False

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip()
        if email and User.objects.filter(email=email).exists():
            raise ValidationError('Ya existe un usuario con este correo.')
        return email

    def clean_password1(self):
        password = self.cleaned_data.get('password1')
        if password:
            validate_password(password)
        return password

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password1')
        p2 = cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', 'Las contraseñas no coinciden.')
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
        return user


# ════════════════════════════════════════════════════════════════════════
# PRODUCTOS — Inventario
# ════════════════════════════════════════════════════════════════════════

from catalogo.models import Categoria, Producto


class ProductoForm(forms.ModelForm):
    """
    Formulario para crear y editar productos desde el panel admin.
    La compresión WebP la maneja el propio model.save().
    """

    class Meta:
        model  = Producto
        fields = [
            'nombre', 'categoria', 'descripcion',
            'precio', 'stock',
            'precio_grande', 'stock_grande',
            'imagen', 'disponible', 'destacado',
        ]
        labels = {
            'nombre':        'Nombre del producto',
            'categoria':     'Categoría',
            'descripcion':   'Descripción',
            'precio':        'Precio Chico (MXN)',
            'stock':         'Stock Chico (unidades)',
            'precio_grande': 'Precio Grande (MXN, Opcional)',
            'stock_grande':  'Stock Grande (unidades, Opcional)',
            'imagen':        'Imagen del producto',
            'disponible':    'Disponible en tienda',
            'destacado':     'Producto destacado',
        }
        help_texts = {
            'imagen':        'La imagen se comprimirá y convertirá a WebP automáticamente.',
            'destacado':     'Aparece en las OFERTAS ESPECIALES de la página de inicio y en la sección de destacados.',
            'disponible':    'Desactívalo para ocultarlo del catálogo sin eliminarlo.',
            'stock':         'Pon 0 si no llevas control de inventario.',
            'precio_grande': 'Precio para el tamaño grande del producto. Dejar vacío si solo hay un tamaño.',
            'stock_grande':  'Número de unidades de tamaño grande disponibles en inventario.',
        }
        widgets = {
            'nombre':        forms.TextInput(),
            'descripcion':   forms.Textarea(attrs={'rows': 3}),
            'precio':        forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'stock':         forms.NumberInput(attrs={'min': '0'}),
            'precio_grande': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'stock_grande':  forms.NumberInput(attrs={'min': '0'}),
            'categoria':     forms.Select(),
        }

    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre', '').strip()
        if not nombre:
            raise ValidationError('El nombre no puede estar vacío.')
        return nombre

    def clean_precio(self):
        precio = self.cleaned_data.get('precio')
        if precio is not None and precio < 0:
            raise ValidationError('El precio no puede ser negativo.')
        return precio

    def clean_precio_grande(self):
        precio_grande = self.cleaned_data.get('precio_grande')
        if precio_grande is not None and precio_grande < 0:
            raise ValidationError('El precio grande no puede ser negativo.')
        return precio_grande

    def clean_stock_grande(self):
        stock_grande = self.cleaned_data.get('stock_grande')
        if stock_grande is not None and stock_grande < 0:
            raise ValidationError('El stock grande no puede ser negativo.')
        return stock_grande


class CategoriaForm(forms.ModelForm):
    """Formulario para crear y editar categorías desde el panel admin."""

    class Meta:
        model = Categoria
        fields = ['nombre', 'descripcion', 'activa', 'orden']
        labels = {
            'nombre': 'Nombre de la categoría',
            'descripcion': 'Descripción',
            'activa': 'Categoría activa',
            'orden': 'Orden de aparición (número)',
        }
        help_texts = {
            'activa': 'Las categorías inactivas se ocultan en el catálogo de cara al cliente.',
            'orden': 'Determina el orden en que se listará en el catálogo (ej. 1, 2, 3...).',
        }
        widgets = {
            'nombre': forms.TextInput(),
            'descripcion': forms.Textarea(attrs={'rows': 2}),
            'orden': forms.NumberInput(attrs={'min': '0'}),
        }

    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre', '').strip()
        if not nombre:
            raise ValidationError('El nombre no puede estar vacío.')
        
        # Validar duplicados sin importar mayúsculas, excluyendo el actual al editar
        qs = Categoria.objects.filter(nombre__iexact=nombre)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError('Ya existe una categoría con este nombre.')
        return nombre


