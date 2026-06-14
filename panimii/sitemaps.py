from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from catalogo.models import Categoria

class StaticViewSitemap(Sitemap):
    priority = 0.8
    changefreq = 'weekly'

    def items(self):
        return ['home', 'nosotros', 'contacto', 'catalogo:lista']

    def location(self, item):
        return reverse(item)

class CategoriaSitemap(Sitemap):
    priority = 0.7
    changefreq = 'weekly'

    def items(self):
        return Categoria.objects.filter(activa=True)

    def lastmod(self, obj):
        return obj.actualizado
