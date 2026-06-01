from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, render

from .models import Categoria, Producto


def catalogo(request):
    """
    Vista principal del catálogo.

    - Sin filtro: muestra todos los productos disponibles agrupados por categoría.
    - Con ?categoria=<slug>: filtra por esa categoría y la marca como activa
      para resaltar el tab del filtro en el template.
    """
    slug_filtro = request.GET.get('categoria', None)

    # Todas las categorías activas con sus productos precargados (1 query extra)
    categorias = (
        Categoria.objects
        .filter(activa=True)
        .prefetch_related(
            Prefetch(
                'productos',
                queryset=Producto.objects.all().order_by('-disponible', '-destacado', '-creado'),
            )
        )
        .order_by('orden', 'nombre')
    )

    # Filtro por categoría (opcional)
    categoria_activa = None
    if slug_filtro:
        categoria_activa = get_object_or_404(Categoria, slug=slug_filtro, activa=True)
        productos = Producto.objects.filter(
            categoria=categoria_activa,
        ).order_by('-disponible', '-destacado', '-creado')
    else:
        productos = Producto.objects.all().order_by('-disponible', '-destacado', '-creado')

    context = {
        'categorias': categorias,
        'categoria_activa': categoria_activa,
        'productos': productos,
    }
    return render(request, 'catalogo/catalogo.html', context)
