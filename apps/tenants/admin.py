# apps/tenants/admin.py
from django.contrib import admin
from .models import Plan, Modulo, Tenant, TenantModulo

@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'max_usuarios', 'max_productos', 'max_categorias', 'precio_mensual', 'activo')
    list_filter = ('activo',)
    search_fields = ('nombre',)

@admin.register(Modulo)
class ModuloAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'precio_mensual', 'activo')
    list_filter = ('activo',)
    search_fields = ('codigo', 'nombre')

@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ('nombre_negocio', 'email_contacto', 'plan', 'estado', 'fecha_registro', 'fecha_vencimiento')
    list_filter = ('estado', 'plan')
    search_fields = ('nombre_negocio', 'email_contacto')

@admin.register(TenantModulo)
class TenantModuloAdmin(admin.ModelAdmin):
    list_display = ('tenant', 'modulo', 'fecha_activacion', 'activo')
    list_filter = ('activo', 'modulo')