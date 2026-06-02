from django.db import transaction  # ← agregar este import
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import api_view, permission_classes as drf_permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied

from .models import Permiso, Rol, RolPermiso
from .serializers import PermisoSerializer, RolSerializer, RolPermisoSerializer
from .permissions import PermisoRequeridoMixin
from .permisos import GESTIONAR_ROLES
from apps.users.models import Usuario


def _verificar_modulo_rbac(user):
    tiene = user.tenant.modulos.filter(modulo__codigo='rbac', activo=True).exists()
    if not tiene:
        raise PermissionDenied('Tu plan no incluye el módulo de usuarios y roles.')


class PermisoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset           = Permiso.objects.all()
    serializer_class   = PermisoSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        _verificar_modulo_rbac(self.request.user)
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
        _verificar_modulo_rbac(self.request.user)
        return Rol.objects.filter(tenant=self.request.user.tenant, activo=True)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.tenant)

    def update(self, request, *args, **kwargs):
        rol = self.get_object()
        if rol.nombre == 'Owner':
            raise PermissionDenied('El rol Owner no puede modificarse.')
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        rol = self.get_object()
        if rol.nombre == 'Owner':
            raise PermissionDenied('El rol Owner no puede eliminarse.')

        with transaction.atomic():
            rol.usuarios.filter(activo=True).update(rol=None)
            rol.activo = False
            rol.save(update_fields=['activo'])

        return Response(status=status.HTTP_204_NO_CONTENT)


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
        _verificar_modulo_rbac(self.request.user)
        return RolPermiso.objects.filter(rol__tenant=self.request.user.tenant)

    def _es_owner(self):
        return self.request.user.rol.nombre == 'Owner'

    def _permiso_es_owner(self, permiso_id):
        try:
            return Permiso.objects.get(id=permiso_id).codigo == GESTIONAR_ROLES
        except Permiso.DoesNotExist:
            return False

    def create(self, request, *args, **kwargs):
        _verificar_modulo_rbac(request.user)
        permiso_id = request.data.get('permiso')
        rol_id     = request.data.get('rol')

        if self._permiso_es_owner(permiso_id) and not self._es_owner():
            raise PermissionDenied('Solo un Owner puede otorgar permisos de gestión de roles.')

        try:
            rol = Rol.objects.get(id=rol_id, tenant=request.user.tenant)
            if rol.nombre == 'Owner':
                raise PermissionDenied('Los permisos del rol Owner no pueden modificarse.')
        except Rol.DoesNotExist:
            pass

        return super().create(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        _verificar_modulo_rbac(request.user)
        rol_permiso = self.get_object()

        if rol_permiso.rol.nombre == 'Owner':
            raise PermissionDenied('Los permisos del rol Owner no pueden modificarse.')

        if (rol_permiso.permiso.codigo == GESTIONAR_ROLES
                and self._es_owner()
                and request.user.rol == rol_permiso.rol):
            raise PermissionDenied('No puedes revocar tu propio permiso de Owner.')

        return super().destroy(request, *args, **kwargs)


@api_view(['GET'])
@drf_permission_classes([IsAuthenticated])
def rbac_stats(request):
    _verificar_modulo_rbac(request.user)
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