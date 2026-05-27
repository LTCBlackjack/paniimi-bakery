import subprocess
import sys

def run_cmd(cmd):
    try:
        print(f"=== Ejecutando: {cmd} ===")
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("ERRORES:")
            print(result.stderr)
        print("="*40)
    except Exception as e:
        print(f"Error al ejecutar {cmd}: {str(e)}")

if __name__ == "__main__":
    # 1. Actualizar pip
    run_cmd(f"{sys.executable} -m pip install --upgrade pip")
    
    # 2. Instalar dependencias
    run_cmd(f"{sys.executable} -m pip install -r requirements.txt")
    
    # 3. Correr migraciones
    run_cmd(f"{sys.executable} manage.py migrate")
    
    print("¡PROCESO TERMINADO! Revisa los logs arriba para ver si hubo errores.")
