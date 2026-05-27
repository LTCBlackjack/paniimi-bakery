import subprocess
import sys

print("--- INSTALADOR PIP DE EMERGENCIA DE PANIIMI ---")
try:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    print("SUCCESS: Librerias instaladas correctamente en el entorno virtual.")
except Exception as e:
    print(f"ERROR: No se pudo completar la instalacion: {str(e)}")
