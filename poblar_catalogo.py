import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'panimii.settings')
django.setup()

from catalogo.models import Categoria, Producto

def poblar():
    print("Iniciando población de catálogo de prueba...")

    # Limpiar catálogo existente
    Producto.objects.all().delete()
    Categoria.objects.all().delete()
    print("Base de datos de catálogo limpiada.")

    # 1. Crear Categorías
    cat_pan = Categoria.objects.create(
        nombre="Pan Artesanal",
        descripcion="Pan de fermentación lenta, crujiente por fuera y suave por dentro.",
        orden=1
    )
    cat_reposteria = Categoria.objects.create(
        nombre="Repostería Fina",
        descripcion="Hojaldres de mantequilla pura, tartas exquisitas y postres del día.",
        orden=2
    )
    cat_bebidas = Categoria.objects.create(
        nombre="Cafetería y Bebidas",
        descripcion="Café de especialidad de origen local y bebidas calientes o frías.",
        orden=3
    )
    print("Categorías creadas con éxito.")

    # 2. Crear Productos - Pan Artesanal
    p1 = Producto.objects.create(
        nombre="Pan de Masa Madre",
        descripcion="Pan rústico de masa madre de trigo integral, fermentación de 24 horas en frío. Excelente textura y sabor ligeramente ácido.",
        precio=85.00,
        categoria=cat_pan,
        disponible=True,
        destacado=True,
        stock=15
    )
    p2 = Producto.objects.create(
        nombre="Baguette Rústica",
        descripcion="Baguette francesa tradicional elaborada con harina de trigo de alta calidad, corteza crujiente y alveolado perfecto.",
        precio=45.00,
        categoria=cat_pan,
        disponible=True,
        destacado=True,
        stock=20
    )
    p3 = Producto.objects.create(
        nombre="Ciabatta de Olivas",
        descripcion="Pan italiano suave con aceite de oliva extra virgen y aceitunas negras Kalamata troceadas.",
        precio=55.00,
        categoria=cat_pan,
        disponible=True,
        destacado=False,
        stock=12
    )

    # 3. Crear Productos - Repostería Fina
    p4 = Producto.objects.create(
        nombre="Croissant de Mantequilla",
        descripcion="Hojaldre clásico francés elaborado con mantequilla pura al 100%. Capas crujientes y miga aireada y ligera.",
        precio=38.00,
        categoria=cat_reposteria,
        disponible=True,
        destacado=True,
        stock=25
    )
    p5 = Producto.objects.create(
        nombre="Pain au Chocolat",
        descripcion="Tradicional pan de chocolate hojaldrado relleno con dos barras de chocolate semi-amargo de alta calidad.",
        precio=42.00,
        categoria=cat_reposteria,
        disponible=True,
        destacado=True,
        stock=18
    )
    p6 = Producto.objects.create(
        nombre="Tarta de Limón y Merengue",
        descripcion="Base crujiente de masa sablé, crema ácida de limón natural y copete alto de merengue italiano flameado.",
        precio=65.00,
        categoria=cat_reposteria,
        disponible=True,
        destacado=False,
        stock=8
    )

    # 4. Crear Productos - Bebidas
    p7 = Producto.objects.create(
        nombre="Espresso Doble",
        descripcion="Extracción doble de espresso corto utilizando granos de especialidad con notas achocolatadas.",
        precio=35.00,
        categoria=cat_bebidas,
        disponible=True,
        destacado=False,
        stock=100
    )
    p8 = Producto.objects.create(
        nombre="Latte de Vainilla",
        descripcion="Café espresso con leche cremada al vapor y un toque suave de jarabe artesanal de vainilla de Papantla.",
        precio=50.00,
        categoria=cat_bebidas,
        disponible=True,
        destacado=False,
        stock=100
    )
    p9 = Producto.objects.create(
        nombre="Matcha Latte Orgánico",
        descripcion="Té matcha ceremonial orgánico de Japón, batido tradicionalmente y mezclado con leche cremada de tu elección.",
        precio=60.00,
        categoria=cat_bebidas,
        disponible=True,
        destacado=False,
        stock=50
    )

    print("Productos creados con éxito.")
    print("¡Población completada exitosamente!")

if __name__ == '__main__':
    poblar()
