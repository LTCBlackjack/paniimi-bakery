import os
import django

# Iniciar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'panimii.settings')
django.setup()

from django.contrib.auth.models import User

# Configuracion del admin
USERNAME = "admin"
EMAIL = "admin@paniimibakery.com"
PASSWORD = "PasswordSegura123!"

try:
    if not User.objects.filter(username=USERNAME).exists():
        user = User.objects.create_superuser(USERNAME, EMAIL, PASSWORD)
        print(f"¡EXITO! Usuario administrador creado.")
        print(f"Usuario: {USERNAME}")
        print(f"Contraseña: {PASSWORD}")
    else:
        print("El usuario administrador ya existe.")
        
        # Opcional: forzar actualización de contraseña si ya existe
        user = User.objects.get(username=USERNAME)
        user.set_password(PASSWORD)
        user.save()
        print(f"La contraseña ha sido actualizada a: {PASSWORD}")
        
except Exception as e:
    print(f"Hubo un error: {str(e)}")
