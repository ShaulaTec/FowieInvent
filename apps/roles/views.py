# apps/roles/views.py
from rest_framework import viewsets, permissions
from .models import Permiso, Rol, RolPermiso
from .serializers import PermisoSerializer, RolSerializer, RolPermisoSerializer
from .permissions import PermisoRequeridoMixin
from .permisos import GESTIONAR_ROLES


class PermisoViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Solo lectura — el catalogo de permisos lo define el sistema (FR08),
    asi que cualquier usuario autenticado puede consultarlo para construir
    los formularios de roles. No requiere un permiso extra.
    """
    queryset = Permiso.objects.all()
    serializer_class = PermisoSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        modulos_activos = self.request.user.tenant.modulos.filter(
            activo=True
        ).values_list('modulo__codigo', flat=True)
        return Permiso.objects.filter(modulo__codigo__in=modulos_activos).select_related('modulo')


class RolViewSet(PermisoRequeridoMixin, viewsets.ModelViewSet):
    serializer_class = RolSerializer
    permission_classes = [permissions.IsAuthenticated]
    permiso_requerido_map = {
        'list':           GESTIONAR_ROLES,
        'retrieve':       GESTIONAR_ROLES,
        'create':         GESTIONAR_ROLES,
        'update':         GESTIONAR_ROLES,
        'partial_update': GESTIONAR_ROLES,
        'destroy':        GESTIONAR_ROLES,
    }

    def get_queryset(self):
        return Rol.objects.filter(
            tenant=self.request.user.tenant,
            activo=True
        )

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.tenant)


class RolPermisoViewSet(PermisoRequeridoMixin, viewsets.ModelViewSet):
    serializer_class = RolPermisoSerializer
    permission_classes = [permissions.IsAuthenticated]
    permiso_requerido_map = {
        'list':           GESTIONAR_ROLES,
        'retrieve':       GESTIONAR_ROLES,
        'create':         GESTIONAR_ROLES,
        'update':         GESTIONAR_ROLES,
        'partial_update': GESTIONAR_ROLES,
        'destroy':        GESTIONAR_ROLES,
    }

    def get_queryset(self):
        return RolPermiso.objects.filter(
            rol__tenant=self.request.user.tenant
        )
