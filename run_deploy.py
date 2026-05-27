import subprocess
import sys

print("--- INICIANDO DESPLIEGUE DE PANIIMI BAKERY ---")
try:
    # 1. Ejecutar las migraciones de la base de datos
    print("1. Ejecutando migraciones...")
    subprocess.check_call([sys.executable, "manage.py", "migrate"])
    
    # 2. Recolectar archivos estáticos
    print("2. Recolectando archivos estaticos...")
    subprocess.check_call([sys.executable, "manage.py", "collectstatic", "--noinput"])
    
    print("SUCCESS: Despliegue completado con exito en produccion.")
except Exception as e:
    print(f"ERROR durante el despliegue: {str(e)}")
