import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'panimii.settings')
django.setup()

from catalogo.models import Categoria, Producto

def poblar():
    print("Iniciando población de catálogo de prueba con Roles y Cookies...")

    # Limpiar catálogo existente
    Producto.objects.all().delete()
    Categoria.objects.all().delete()
    print("Base de datos de catálogo limpiada.")

    # 1. Crear Categorías
    cat_roles = Categoria.objects.create(
        nombre="Roles",
        descripcion="Exquisitos roles recién horneados, suaves y con deliciosas coberturas.",
        orden=1
    )
    cat_cookies = Categoria.objects.create(
        nombre="Cookies",
        descripcion="Cookies artesanales crujientes por fuera y súper suaves por dentro, preparadas con ingredientes selectos.",
        orden=2
    )
    print("Categorías 'Roles' y 'Cookies' creadas con éxito.")

    # 2. Crear Productos - Roles
    p1 = Producto.objects.create(
        nombre="Rol de Canela Clásico",
        descripcion="Delicioso rol de canela súper esponjoso, glaseado con queso crema suave y un toque de vainilla.",
        precio=45.00,
        categoria=cat_roles,
        disponible=True,
        destacado=True,
        stock=15
    )
    p2 = Producto.objects.create(
        nombre="Rol de Canela y Nuez",
        descripcion="Nuestro clásico rol de canela espolvoreado con abundantes trozos de nuez pecana tostada y crujiente.",
        precio=50.00,
        categoria=cat_roles,
        disponible=True,
        destacado=True,
        stock=12
    )
    p3 = Producto.objects.create(
        nombre="Rol de Chocolate",
        descripcion="Esponjoso rol relleno de crema de chocolate semi-amargo y bañado con ganache de chocolate.",
        precio=48.00,
        categoria=cat_roles,
        disponible=True,
        destacado=False,
        stock=10
    )

    # 3. Crear Productos - Cookies
    p4 = Producto.objects.create(
        nombre="Choco Chip Cookie",
        descripcion="La clásica cookie dorada por fuera y súper masticable por dentro, cargada de abundantes chispas de chocolate semi-amargo.",
        precio=35.00,
        categoria=cat_cookies,
        disponible=True,
        destacado=True,
        stock=25
    )
    p5 = Producto.objects.create(
        nombre="Red Velvet Cookie",
        descripcion="Hermosa cookie color rojo aterciopelado con un toque de cocoa y deliciosos trozos de chocolate blanco.",
        precio=38.00,
        categoria=cat_cookies,
        disponible=True,
        destacado=True,
        stock=20
    )
    p6 = Producto.objects.create(
        nombre="Oatmeal Raisin Cookie",
        descripcion="Cookie rústica y nutritiva elaborada con hojuelas de avena entera, pasas selectas y un toque sutil de canela.",
        precio=32.00,
        categoria=cat_cookies,
        disponible=True,
        destacado=False,
        stock=18
    )

    print("Productos de Roles y Cookies creados con éxito.")
    print("¡Población completada exitosamente!")

if __name__ == '__main__':
    poblar()
