"""
Django settings for panimii project.

Las credenciales sensibles (SECRET_KEY, email, DB) se cargan desde el
archivo .env usando python-dotenv. Nunca escribas valores reales aquí.
Consulta .env.example para ver las variables requeridas.
"""

from pathlib import Path

from dotenv import load_dotenv
import os

# ── Cargar variables del archivo .env ───────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')


# ════════════════════════════════════════════════════════════════════════
# SEGURIDAD
# ════════════════════════════════════════════════════════════════════════
SECRET_KEY = os.environ['SECRET_KEY']

DEBUG = os.getenv('DEBUG', 'False') == 'True'

#ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1', '*').split(',')

ALLOWED_HOSTS = ['*']
# ════════════════════════════════════════════════════════════════════════
# APLICACIONES
# ════════════════════════════════════════════════════════════════════════
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Apps propias
    'catalogo',
    'panel_admin',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'panimii.middleware.AdminKeyfileMiddleware',
]

ROOT_URLCONF = 'panimii.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'panimii.context_processors.carrito_count',
                'panimii.context_processors.temporada_activa',
            ],
        },
    },
]

WSGI_APPLICATION = 'panimii.wsgi.application'


# ════════════════════════════════════════════════════════════════════════
# BASE DE DATOS
# Lee ENGINE y NAME del .env; soporte para SQLite (dev) y MySQL (prod).
# ════════════════════════════════════════════════════════════════════════
_db_engine = os.getenv('DB_ENGINE', 'django.db.backends.sqlite3')
_db_name   = os.getenv('DB_NAME', 'db.sqlite3')

if _db_engine == 'django.db.backends.sqlite3':
    DATABASES = {
        'default': {
            'ENGINE': _db_engine,
            'NAME':   BASE_DIR / _db_name,
        }
    }
else:
    # MySQL / PostgreSQL — todas las credenciales vienen del .env
    DATABASES = {
        'default': {
            'ENGINE':   _db_engine,
            'NAME':     _db_name,
            'USER':     os.getenv('DB_USER', ''),
            'PASSWORD': os.getenv('DB_PASSWORD', ''),
            'HOST':     os.getenv('DB_HOST', 'localhost'),
            'PORT':     os.getenv('DB_PORT', '3306'),
        }
    }


# ════════════════════════════════════════════════════════════════════════
# VALIDACIÓN DE CONTRASEÑAS
# ════════════════════════════════════════════════════════════════════════
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# ════════════════════════════════════════════════════════════════════════
# INTERNACIONALIZACIÓN
# ════════════════════════════════════════════════════════════════════════
LANGUAGE_CODE = 'es-mx'
TIME_ZONE     = 'America/Mexico_City'
USE_I18N      = True
USE_TZ        = True


# ════════════════════════════════════════════════════════════════════════
# ARCHIVOS ESTÁTICOS Y MEDIA
# ════════════════════════════════════════════════════════════════════════
STATIC_URL       = 'static/'
STATIC_ROOT      = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL  = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── Autenticación ────────────────────────────────────────────────────────────
LOGIN_URL           = '/auth/login/'
LOGIN_REDIRECT_URL  = '/'
LOGOUT_REDIRECT_URL = '/'

AUTHENTICATION_BACKENDS = [
    'panimii.backends.EmailOrUsernameModelBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# ── Stripe ───────────────────────────────────────────────────────────────────
STRIPE_PUBLIC_KEY = os.getenv('STRIPE_PUBLIC_KEY', '')
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY', '')

# ── Configuración SPEI y WhatsApp (Flujo de Pago Local) ──────────────────────
BANK_NAME = os.getenv('BANK_NAME', 'Banco de Prueba')
BANK_CLABE = os.getenv('BANK_CLABE', '000000000000000000')
BANK_BENEFICIARY = os.getenv('BANK_BENEFICIARY', 'Paniimi Bakery')
WHATSAPP_PHONE = os.getenv('WHATSAPP_PHONE', '529991234567')



# ════════════════════════════════════════════════════════════════════════
# CORREO ELECTRÓNICO — SMTP
#
# Todas las credenciales se cargan desde .env.
# Para Gmail:
#   1. Activa la verificación en dos pasos en tu cuenta Google.
#   2. Ve a https://myaccount.google.com/apppasswords
#   3. Genera una "Contraseña de aplicación" y pégala en EMAIL_HOST_PASSWORD.
# ════════════════════════════════════════════════════════════════════════
EMAIL_BACKEND      = 'panimii.email_backend.CpanelSafeEmailBackend'
EMAIL_HOST         = os.getenv('EMAIL_HOST',         'smtp.gmail.com')
EMAIL_PORT         = int(os.getenv('EMAIL_PORT',     '587'))
EMAIL_USE_TLS      = os.getenv('EMAIL_USE_TLS',      'True') == 'True'
EMAIL_USE_SSL      = os.getenv('EMAIL_USE_SSL',      'False') == 'True'
EMAIL_HOST_USER    = os.getenv('EMAIL_HOST_USER',    '')
EMAIL_HOST_PASSWORD= os.getenv('EMAIL_HOST_PASSWORD','')
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

# Dirección interna que recibe los mensajes del formulario de contacto
EMAIL_DESTINATARIO = os.getenv('EMAIL_DESTINATARIO', EMAIL_HOST_USER)



# ════════════════════════════════════════════════════════════════════════
# ENTORNO TEMPORAL (trycloudflare)
# ════════════════════════════════════════════════════════════════════════
CSRF_TRUSTED_ORIGINS = ['https://*.trycloudflare.com']