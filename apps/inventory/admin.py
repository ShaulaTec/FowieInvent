# apps/inventory/admin.py
from django.contrib import admin
from .models import Categoria, Producto, Movimiento

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tenant', 'activo')
    list_filter = ('activo', 'tenant')
    search_fields = ('nombre',)

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tenant', 'categoria', 'stock_actual', 'stock_minimo', 'activo')
    list_filter = ('activo', 'tenant', 'categoria')
    search_fields = ('nombre',)

@admin.register(Movimiento)
class MovimientoAdmin(admin.ModelAdmin):
    list_display = ('producto', 'usuario', 'tipo', 'cantidad', 'fecha')
    list_filter = ('tipo',)
    search_fields = ('producto__nombre',)