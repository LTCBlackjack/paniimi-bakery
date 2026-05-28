from django.shortcuts import redirect
from django.urls import reverse

class AdminKeyfileMiddleware:
    """
    Middleware de Django que intercepta cualquier petición dirigida al panel (/panel/...)
    para usuarios con rol de administrador (staff/superuser) y restringe su acceso hasta que
    hayan subido y verificado su archivo de llave criptográfica única (.key).
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Interceptar únicamente rutas del panel administrativo personalizado
        if request.path.startswith('/panel/'):
            if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
                # Rutas exentas de validación para permitir la autenticación y descarga
                exceptuadas = [
                    reverse('panel_admin:verificar_llave'),
                    reverse('panel_admin:solicitar_llave'),
                    reverse('panel_admin:descargar_llave_directa'),
                ]
                es_descarga = request.path.startswith('/panel/descargar-llave/')

                # Si no ha verificado su llave física y está fuera de las excepciones, redirigir
                if not request.session.get('admin_key_verified', False):
                    if request.path not in exceptuadas and not es_descarga:
                        return redirect('panel_admin:verificar_llave')

        response = self.get_response(request)
        return response
