"""
Backend de correo para Paniimi Bakery en hosting compartido (cPanel).

El servidor tiene un proxy/firewall que intercepta las conexiones SMTP
en el puerto 587 (STARTTLS) y presenta un certificado SSL propio que
no coincide con smtp.gmail.com, causando CERTIFICATE_VERIFY_FAILED.

Solucion: usar el puerto 465 con SSL directo (SMTPS) y un contexto
SSL que no verifique el hostname del certificado. Esto establece la
conexion cifrada desde el inicio, evitando el proxy STARTTLS.
"""
import ssl
import smtplib
from django.core.mail.backends.smtp import EmailBackend as SmtpEmailBackend


class CpanelSafeEmailBackend(SmtpEmailBackend):
    """
    Backend SMTP que fuerza conexion SSL directa en puerto 465
    con verificacion de certificado relajada.
    """

    def open(self):
        if self.connection:
            return False

        # Contexto SSL que no verifica el hostname del certificado
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        try:
            # Forzar SMTP_SSL en puerto 465 (SSL directo, no STARTTLS)
            self.connection = smtplib.SMTP_SSL(
                self.host,
                465,
                context=context,
            )

            # Autenticarse con Gmail
            if self.username and self.password:
                self.connection.login(self.username, self.password)

            return True
        except Exception:
            if not self.fail_silently:
                raise
