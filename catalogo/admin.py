from django.contrib import admin

from .models import Categoria, Orden, OrdenItem, Producto


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'activa', 'orden', 'creado')
    list_editable = ('activa', 'orden')
    list_filter = ('activa',)
    search_fields = ('nombre',)
    prepopulated_fields = {'slug': ('nombre',)}


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'categoria', 'precio', 'stock', 'disponible', 'destacado', 'creado')
    list_editable = ('precio', 'stock', 'disponible', 'destacado')
    list_filter = ('categoria', 'disponible', 'destacado')
    search_fields = ('nombre', 'descripcion', 'codigo')
    prepopulated_fields = {'slug': ('nombre',)}
    raw_id_fields = ('categoria',)
    readonly_fields = ('codigo',)


class OrdenItemInline(admin.TabularInline):
    model = OrdenItem
    extra = 0
    readonly_fields = ('subtotal',)

    def subtotal(self, obj):
        return f'${obj.subtotal():.2f}'
    subtotal.short_description = 'Subtotal'


@admin.register(Orden)
class OrdenAdmin(admin.ModelAdmin):
    list_display = ('pk', 'cliente', 'total', 'estado', 'creado')
    list_filter = ('estado',)
    search_fields = ('cliente__username', 'email_cliente')
    readonly_fields = ('creado', 'actualizado')
    inlines = [OrdenItemInline]

