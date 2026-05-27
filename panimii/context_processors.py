"""
Context processors globales de Paniimi Bakery.
Se registran en TEMPLATES → context_processors en settings.py.
"""


def carrito_count(request):
    """
    Inyecta `carrito_count` en todos los templates.

    Cuenta el total de unidades en el carrito de sesión para que
    el indicador del navbar (Carrito (N)) se actualice en tiempo real
    sin necesidad de pasar el dato manualmente en cada vista.
    """
    carrito = request.session.get('carrito', {})
    count = sum(item.get('cantidad', 0) for item in carrito.values())
    return {'carrito_count': count}


def temporada_activa(request):
    """
    Inyecta `temporada_activa` (ej. 'original', 'primavera', etc.) en todos los templates.
    """
    from catalogo.models import ConfiguracionTemporada
    return {'temporada_activa': ConfiguracionTemporada.get_activa()}

