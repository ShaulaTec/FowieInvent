# apps/roles/admin.py
from django.contrib import admin
from .models import Permiso, Rol, RolPermiso

class RolPermisoInline(admin.TabularInline):
    model = RolPermiso
    extra = 1

@admin.register(Permiso)
class PermisoAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'modulo', 'submodulo', 'ruta', 'icono', 'descripcion')
    list_filter = ('modulo', 'submodulo')
    search_fields = ('codigo', 'descripcion')
    ordering = ('modulo', 'submodulo', 'codigo')

@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tenant', 'activo')
    list_filter = ('activo',)
    search_fields = ('nombre', 'tenant__nombre_negocio')
    inlines = [RolPermisoInline]  # ver/editar permisos del rol inline

@admin.register(RolPermiso)
class RolPermisoAdmin(admin.ModelAdmin):
    list_display = ('rol', 'permiso')
    list_filter = ('rol__tenant', 'permiso__modulo')