from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from catalogo.models import DireccionEnvio


class ContactoForm(forms.Form):
    """
    Formulario de contacto / pedidos especiales.
    La validación se hace en Django; no usa modelos.
    """
    nombre = forms.CharField(
        max_length=100,
        label='Nombre completo',
        widget=forms.TextInput(attrs={
            'placeholder': 'Tu nombre',
            'id': 'id_nombre',
            'autocomplete': 'name',
        }),
        error_messages={'required': 'Por favor escribe tu nombre.'},
    )
    email = forms.EmailField(
        label='Correo electrónico',
        widget=forms.EmailInput(attrs={
            'placeholder': 'correo@ejemplo.com',
            'id': 'id_email',
            'autocomplete': 'email',
        }),
        error_messages={
            'required': 'Por favor escribe tu correo.',
            'invalid': 'Ingresa un correo válido.',
        },
    )
    mensaje = forms.CharField(
        label='Mensaje o pedido especial',
        widget=forms.Textarea(attrs={
            'placeholder': '¿Qué tienes en mente? Cuéntanos tu pedido, sabor favorito, fecha de entrega...',
            'rows': 6,
            'id': 'id_mensaje',
        }),
        error_messages={'required': 'Por favor escribe tu mensaje.'},
    )


class RegistroForm(UserCreationForm):
    """
    Formulario de registro público.

    Extiende UserCreationForm añadiendo el campo email (requerido)
    y traduciendo los labels/mensajes de error al español.
    """
    email = forms.EmailField(
        required=True,
        label='Correo electrónico',
        widget=forms.EmailInput(attrs={
            'placeholder': 'correo@ejemplo.com',
            'autocomplete': 'email',
        }),
        error_messages={
            'required': 'Por favor ingresa tu correo.',
            'invalid':  'Ingresa un correo válido.',
        },
    )

    class Meta:
        model  = User
        fields = ('username', 'email', 'password1', 'password2')
        labels = {
            'username': 'Nombre de usuario',
        }
        widgets = {
            'username': forms.TextInput(attrs={
                'placeholder': 'tu_usuario',
                'autocomplete': 'username',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Traducir placeholders y labels de los campos heredados
        self.fields['password1'].label   = 'Contraseña'
        self.fields['password2'].label   = 'Confirmar contraseña'
        self.fields['password1'].widget  = forms.PasswordInput(attrs={
            'placeholder': '••••••••',
            'autocomplete': 'new-password',
        })
        self.fields['password2'].widget  = forms.PasswordInput(attrs={
            'placeholder': '••••••••',
            'autocomplete': 'new-password',
        })
        # Quitar los textos de ayuda genéricos de Django
        for field in self.fields.values():
            field.help_text = ''

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user


class DireccionEntregaForm(forms.Form):
    """
    Captura los datos de entrega durante el checkout.
    Se usa junto con el PaymentMethod de Stripe.
    """
    telefono = forms.CharField(
        max_length=20,
        label='Teléfono de contacto',
        widget=forms.TextInput(attrs={
            'placeholder': '999 123 4567',
            'autocomplete': 'tel',
        }),
    )
    calle = forms.CharField(
        max_length=200,
        label='Calle y número',
        widget=forms.TextInput(attrs={
            'placeholder': 'Calle 60 #123',
            'autocomplete': 'street-address',
        }),
    )
    colonia = forms.CharField(
        max_length=100,
        label='Colonia',
        widget=forms.TextInput(attrs={'placeholder': 'Centro Histórico'}),
    )
    ciudad = forms.CharField(
        max_length=100,
        label='Ciudad',
        initial='Mérida',
        widget=forms.TextInput(attrs={'placeholder': 'Mérida'}),
    )
    estado_mx = forms.CharField(
        max_length=50,
        label='Estado',
        initial='Yucatán',
        widget=forms.TextInput(attrs={'placeholder': 'Yucatán'}),
    )
    codigo_postal = forms.CharField(
        max_length=10,
        label='Código postal',
        widget=forms.TextInput(attrs={
            'placeholder': '97000',
            'autocomplete': 'postal-code',
            'inputmode': 'numeric',
        }),
    )
    referencias = forms.CharField(
        required=False,
        label='Referencias (opcional)',
        widget=forms.Textarea(attrs={
            'placeholder': 'Casa azul con portón negro, junto al OXXO...',
            'rows': 2,
        }),
    )


class DireccionEnvioForm(forms.ModelForm):
    """
    Formulario para crear y editar direcciones de envío guardadas.
    Mapeado directamente al modelo DireccionEnvio en PostgreSQL.
    """
    class Meta:
        model = DireccionEnvio
        fields = [
            'alias', 'telefono', 'calle', 'colonia',
            'ciudad', 'estado_mx', 'codigo_postal',
            'referencias', 'predetermina'
        ]
        widgets = {
            'alias': forms.TextInput(attrs={
                'placeholder': 'Ej: Mi Casa, Oficina',
                'class': 'field-input'
            }),
            'telefono': forms.TextInput(attrs={
                'placeholder': '999 123 4567',
                'autocomplete': 'tel',
                'class': 'field-input'
            }),
            'calle': forms.TextInput(attrs={
                'placeholder': 'Calle 60 #123',
                'autocomplete': 'street-address',
                'class': 'field-input'
            }),
            'colonia': forms.TextInput(attrs={
                'placeholder': 'Centro',
                'class': 'field-input'
            }),
            'ciudad': forms.TextInput(attrs={
                'placeholder': 'Mérida',
                'class': 'field-input'
            }),
            'estado_mx': forms.TextInput(attrs={
                'placeholder': 'Yucatán',
                'class': 'field-input'
            }),
            'codigo_postal': forms.TextInput(attrs={
                'placeholder': '97000',
                'inputmode': 'numeric',
                'autocomplete': 'postal-code',
                'class': 'field-input'
            }),
            'referencias': forms.Textarea(attrs={
                'placeholder': 'Casa azul, portón de rejas, frente a la escuela...',
                'rows': 2,
                'class': 'field-input resize-none'
            }),
            'predetermina': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-primary border-gray-300 rounded focus:ring-primary'
            }),
        }

