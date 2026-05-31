"""URLs del Panel de Administración Personalizado."""
from django.urls import path

from . import views

app_name = 'panel_admin'

urlpatterns = [
    # Resumen General
    path('', views.resumen, name='resumen'),

    # Gestión de Pedidos
    path('pedidos/', views.pedidos, name='pedidos'),
    path('pedidos/<int:orden_id>/', views.detalle_pedido, name='detalle_pedido'),

    # Inventario — CRUD
    path('inventario/',                          views.inventario,          name='inventario'),
    path('inventario/nuevo/',                    views.crear_producto,      name='crear_producto'),
    path('inventario/<int:producto_id>/editar/', views.editar_producto,     name='editar_producto'),
    path('inventario/<int:producto_id>/eliminar/', views.eliminar_producto, name='eliminar_producto'),

    # Clientes — CRUD
    path('clientes/',                      views.clientes,           name='clientes'),
    path('clientes/nuevo/',                views.crear_cliente,      name='crear_cliente'),
    path('clientes/<int:user_id>/editar/', views.editar_cliente,     name='editar_cliente'),
    path('clientes/<int:user_id>/eliminar/', views.eliminar_cliente, name='eliminar_cliente'),

    # Estaciones
    path('estaciones/', views.estaciones, name='estaciones'),

    # Seguridad — Llaves Criptográficas
    path('verificar-llave/', views.verificar_llave, name='verificar_llave'),
    path('solicitar-llave/', views.solicitar_llave, name='solicitar_llave'),
    path('descargar-llave/<str:uidb64>/<str:token>/', views.descargar_llave, name='descargar_llave'),
    path('descargar-llave-directa/', views.descargar_llave_directa, name='descargar_llave_directa'),

    # Gestión de Llaves (solo admin principal)
    path('seguridad/llaves/', views.gestionar_llaves, name='gestionar_llaves'),
    path('seguridad/llaves/<int:user_id>/generar/', views.generar_llave_usuario, name='generar_llave_usuario'),

    # Diagnóstico (solo admin principal)
    path('diagnostico/email/', views.diagnostico_email, name='diagnostico_email'),
]
