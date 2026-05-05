# apps/users/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario

@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ('email', 'tenant', 'rol', 'activo', 'ultimo_acceso')
    list_filter = ('activo', 'tenant')
    search_fields = ('email', 'tenant__nombre_negocio')