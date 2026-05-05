# apps/roles/admin.py
from django.contrib import admin
from .models import Permiso, Rol, RolPermiso

@admin.register(Permiso)
class PermisoAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'modulo', 'descripcion')
    list_filter = ('modulo',)
    search_fields = ('codigo',)

@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tenant', 'activo')
    list_filter = ('activo',)
    search_fields = ('nombre', 'tenant__nombre_negocio')
    
@admin.register(RolPermiso)
class RolPermisoAdmin(admin.ModelAdmin):
    list_display = ('rol', 'permiso')
    list_filter = ('rol', 'permiso')