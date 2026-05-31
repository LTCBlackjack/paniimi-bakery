"""
Backend de correo personalizado para Paniimi Bakery.

Soluciona el problema de certificados SSL en servidores compartidos (cPanel)
donde el certificado del proxy no coincide con smtp.gmail.com, causando:
    [SSL: CERTIFICATE_VERIFY_FAILED] hostname mismatch

Este backend crea un contexto SSL que no verifica el hostname del certificado,
permitiendo que la conexion SMTP funcione a traves del proxy del hosting.
"""
import ssl
from django.core.mail.backends.smtp import EmailBackend as SmtpEmailBackend


class CpanelSafeEmailBackend(SmtpEmailBackend):
    """
    Backend SMTP que relaja la verificacion SSL para funcionar
    en servidores compartidos con proxies SMTP intermedios.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Crear un contexto SSL que NO verifique el hostname del certificado
        # Esto es necesario porque el proxy del hosting presenta su propio
        # certificado en lugar del de smtp.gmail.com
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
