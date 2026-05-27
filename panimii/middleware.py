from django.shortcuts import redirect
from django.urls import reverse

class AdminKeyfileMiddleware:
    """
    Middleware temporalmente modificado para permitir el acceso directo al panel
    mientras resolvemos el problema del correo SMTP en el servidor.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Deshabilitamos la redireccion obligatoria por ahora para que puedas entrar
        response = self.get_response(request)
        return response
