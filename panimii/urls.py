"""
URL configuration for panimii project.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from django.views.generic import TemplateView

from . import views as project_views

urlpatterns = [
    # ── Páginas principales ──────────────────────────────────────
    path('', project_views.home, name='home'),
    path('nosotros/', TemplateView.as_view(template_name='nosotros.html'), name='nosotros'),
    path('catalogo/', include('catalogo.urls', namespace='catalogo')),
    path('contacto/', project_views.contacto, name='contacto'),
    path('mi-cuenta/', project_views.dashboard, name='dashboard'),
    path('mi-cuenta/direccion/guardar/', project_views.guardar_direccion_ajax, name='guardar_direccion_ajax'),
    path('mi-cuenta/direccion/eliminar/', project_views.eliminar_direccion_ajax, name='eliminar_direccion_ajax'),
    path('mi-cuenta/direccion/predetermina/', project_views.establecer_predeterminada_ajax, name='establecer_predeterminada_ajax'),

    # ── Carrito ──────────────────────────────────────────────────────────
    path('carrito/', project_views.ver_carrito, name='ver_carrito'),
    path('carrito/agregar/<int:producto_id>/', project_views.agregar_al_carrito, name='agregar_al_carrito'),
    path('carrito/actualizar/<str:producto_id>/', project_views.actualizar_carrito, name='actualizar_carrito'),
    path('carrito/checkout/', project_views.crear_orden_checkout, name='crear_orden_checkout'),
    path('carrito/orden/<int:pk>/', project_views.orden_exito, name='orden_exito'),


    # ── Autenticación ───────────────────────────────────────────
    path('auth/login/', project_views.SmartLoginView.as_view(), name='login'),

    path('auth/logout/', auth_views.LogoutView.as_view(), name='logout'),

    path('auth/registro/', project_views.registro, name='registro'),
    path('auth/registro/pendiente/', TemplateView.as_view(template_name='activation_pending.html'), name='registro_pendiente'),
    path('auth/activar/<uidb64>/<token>/', project_views.activar_cuenta, name='activar_cuenta'),

    # ── Restablecimiento de Contraseña ────────────────────────────
    path('auth/password-reset/',
         auth_views.PasswordResetView.as_view(
             template_name='password_reset_form.html',
             email_template_name='password_reset_email.txt',
             html_email_template_name='password_reset_email.html',
             subject_template_name='password_reset_subject.txt',
             success_url='/auth/password-reset/enviado/'
         ),
         name='password_reset'),

    path('auth/password-reset/enviado/',
         auth_views.PasswordResetDoneView.as_view(
             template_name='password_reset_done.html'
         ),
         name='password_reset_done'),

    path('auth/password-reset/confirmar/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(
             template_name='password_reset_confirm.html',
             success_url='/auth/password-reset/completado/'
         ),
         name='password_reset_confirm'),

    path('auth/password-reset/completado/',
         auth_views.PasswordResetCompleteView.as_view(
             template_name='password_reset_complete.html'
         ),
         name='password_reset_complete'),

    # ── Admin Django ──────────────────────────────────────────────
    path('admin/', admin.site.urls),

    # ── Panel Administrativo Personalizado ────────────────────────
    path('panel/', include('panel_admin.urls', namespace='panel_admin')),
]

# Servir archivos de medios en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
