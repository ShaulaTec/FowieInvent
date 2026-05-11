# apps/users/admin.py
from django.contrib import admin
from .models import Usuario

@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ('email', 'tenant', 'rol', 'activo', 'ultimo_acceso')
    list_filter = ('activo', 'tenant', 'rol')
    search_fields = ('email', 'tenant__nombre_negocio')
    readonly_fields = ('ultimo_acceso',)