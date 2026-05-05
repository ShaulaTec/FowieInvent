# apps/notifications/admin.py
from django.contrib import admin
from .models import Notificacion

@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    list_display = ('tenant', 'tipo', 'modulo', 'leida', 'created_at')
    list_filter = ('leida', 'modulo', 'tipo')
    search_fields = ('tenant__nombre_negocio',)