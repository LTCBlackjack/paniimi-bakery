import os
import sys
import subprocess
import hmac
import hashlib

# Agregar el directorio de la aplicacion al path de Python
base_dir = os.path.dirname(__file__)
sys.path.insert(0, base_dir)

# --- AUTO CONFIGURACION Y LLAVE ---
try:
    public_html = "/home/paniimibakery/public_html"
    
    # Ejecutar las migraciones de la base de datos automáticamente
    subprocess.run([sys.executable, "manage.py", "migrate", "--noinput"], cwd=base_dir)
    
    # Recopilar todos los archivos estaticos
    subprocess.run([sys.executable, "manage.py", "collectstatic", "--noinput"], cwd=base_dir)
    
    # Crear accesos directos en public_html para que Apache pueda mostrarlos
    static_src = os.path.join(base_dir, "staticfiles")
    static_dst = os.path.join(public_html, "static")
    media_src = os.path.join(base_dir, "media")
    media_dst = os.path.join(public_html, "media")
    
    if not os.path.exists(static_dst):
        os.symlink(static_src, static_dst)
    if not os.path.exists(media_dst):
        os.symlink(media_src, media_dst)
        
    # Extraer la llave secreta del servidor y generar el archivo .key real
    from dotenv import load_dotenv
    load_dotenv(os.path.join(base_dir, '.env'))
    secret = os.environ.get('SECRET_KEY', '')
    
    msg = b"admin:admin-key"
    signature = hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()
    
    # Guardar el archivo directamente en la carpeta publica del servidor
    with open(os.path.join(public_html, "admin.key"), "w") as f:
        f.write(f"admin:{signature}")
        
except Exception as e:
    pass
# ---------------------------------------

# Configurar el modulo de settings de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'panimii.settings')

# Importar la aplicacion WSGI de Django
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
