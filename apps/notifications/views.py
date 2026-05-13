# apps/notifications/views.py
from rest_framework import viewsets, permissions
from apps.roles.permissions import PermisoRequeridoMixin
from apps.roles.permisos import VER_INVENTARIO
from .models import Notificacion
from .serializers import NotificacionSerializer


class NotificacionViewSet(PermisoRequeridoMixin, viewsets.ModelViewSet):
    """
    Las notificaciones son visibles para cualquier usuario con acceso al
    inventario; solo el dueno del tenant (Owner) o quien tenga permisos
    administrativos puede crearlas/borrarlas manualmente (las normales se
    generan por eventos).
    """
    serializer_class = NotificacionSerializer
    permission_classes = [permissions.IsAuthenticated]
    permiso_requerido_map = {
        'list':           VER_INVENTARIO,
        'retrieve':       VER_INVENTARIO,
        'create':         'gestionar_usuarios',
        'update':         'gestionar_usuarios',
        'partial_update': VER_INVENTARIO,   # marcar leida
        'destroy':        'gestionar_usuarios',
    }

    def get_queryset(self):
        return Notificacion.objects.filter(
            tenant=self.request.user.tenant
        ).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.tenant)
