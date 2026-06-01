from rest_framework import viewsets, permissions
from rest_framework.decorators import api_view, permission_classes as drf_permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Permiso, Rol, RolPermiso
from .serializers import PermisoSerializer, RolSerializer, RolPermisoSerializer
from .permissions import PermisoRequeridoMixin
from .permisos import GESTIONAR_ROLES
from apps.users.models import Usuario


class PermisoViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Solo lectura — el catálogo de permisos lo define el sistema (FR08),
    así que cualquier usuario autenticado puede consultarlo para construir
    los formularios de roles. No requiere un permiso extra.
    """
    queryset         = Permiso.objects.all()
    serializer_class = PermisoSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        modulos_activos = self.request.user.tenant.modulos.filter(
            activo=True
        ).values_list('modulo__codigo', flat=True)
        return Permiso.objects.filter(
            modulo__codigo__in=modulos_activos
        ).select_related('modulo')


class RolViewSet(PermisoRequeridoMixin, viewsets.ModelViewSet):
    serializer_class   = RolSerializer
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
            activo=True,
        )

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.tenant)


class RolPermisoViewSet(PermisoRequeridoMixin, viewsets.ModelViewSet):
    serializer_class   = RolPermisoSerializer
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


@api_view(['GET'])
@drf_permission_classes([IsAuthenticated])
def rbac_stats(request):
    tenant = request.user.tenant

    roles       = Rol.objects.filter(tenant=tenant, activo=True).prefetch_related('permisos', 'usuarios')
    usuarios_qs = Usuario.objects.filter(tenant=tenant, activo=True)
    modulos_activos = tenant.modulos.filter(activo=True).values_list('modulo__codigo', flat=True)

    roles_data = [
        {
            'id':             str(r.id),
            'nombre':         r.nombre,
            'descripcion':    r.descripcion,
            'total_permisos': r.permisos.count(),
            'total_usuarios': r.usuarios.filter(activo=True).count(),
        }
        for r in roles
    ]

    return Response({
        'totales': {
            'roles':    roles.count(),
            'usuarios': usuarios_qs.count(),
            'permisos': Permiso.objects.filter(modulo__codigo__in=modulos_activos).count(),
        },
        'roles':            roles_data,
        'usuarios_sin_rol': usuarios_qs.filter(rol__isnull=True).count(),
    })