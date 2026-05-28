"""
Backend de correo personalizado para Paniimi Bakery.

Soluciona el problema de certificados SSL en servidores compartidos (cPanel)
donde el certificado del proxy no coincide con smtp.gmail.com, causando:
    [SSL: CERTIFICATE_VERIFY_FAILED] hostname mismatch

Este backend hereda del backend SMTP estándar de Django y desactiva
temporalmente la verificación estricta de certificados SSL solo durante
el envío del correo.
"""
import ssl
from django.core.mail.backends.smtp import EmailBackend as SmtpEmailBackend


class CpanelSafeEmailBackend(SmtpEmailBackend):
    """
    Backend SMTP que relaja la verificación SSL para funcionar
    en servidores compartidos con proxies SMTP intermedios.
    """

    def open(self):
        # Guardar el contexto SSL original
        self._original_context = ssl._create_default_https_context

        # Usar un contexto que no verifique el hostname del certificado
        ssl._create_default_https_context = ssl._create_unverified_context

        try:
            result = super().open()
        except Exception:
            # Restaurar en caso de error
            ssl._create_default_https_context = self._original_context
            raise

        return result

    def close(self):
        try:
            super().close()
        finally:
            # Siempre restaurar el contexto SSL original
            if hasattr(self, '_original_context'):
                ssl._create_default_https_context = self._original_context
