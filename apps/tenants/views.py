# apps/tenants/views.py
from django.utils import timezone

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.roles.permissions import (
    PermisoRequeridoMixin,
    usuario_tiene_permiso,
)
from apps.roles.permisos import EDITAR_MI_NEGOCIO, VER_MI_NEGOCIO

from .models import Plan, Modulo, Tenant, TenantModulo
from .serializers import (
    PlanSerializer,
    ModuloSerializer,
    TenantSerializer,
    TenantModuloSerializer,
)


class PlanViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Plan.objects.filter(activo=True)
    serializer_class = PlanSerializer
    permission_classes = [permissions.AllowAny]


class ModuloViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Modulo.objects.filter(activo=True)
    serializer_class = ModuloSerializer
    permission_classes = [permissions.IsAuthenticated]


class TenantViewSet(PermisoRequeridoMixin, viewsets.ModelViewSet):
    serializer_class = TenantSerializer
    permission_classes = [permissions.IsAuthenticated]
    permiso_requerido_map = {
        'list':           VER_MI_NEGOCIO,
        'retrieve':       VER_MI_NEGOCIO,
        'update':         EDITAR_MI_NEGOCIO,
        'partial_update': EDITAR_MI_NEGOCIO,
        # `destroy` queda fuera del mapa: la baja se hace via la accion
        # `cancelar_suscripcion` para que sea explicita y revisable.
    }

    def get_queryset(self):
        return Tenant.objects.filter(id=self.request.user.tenant.id)

    # ─── Cancelar suscripcion ─────────────────────────────────────────────
    @action(detail=False, methods=['post'], url_path='cancelar-suscripcion')
    def cancelar_suscripcion(self, request):
        """
        POST /api/tenants/info/cancelar-suscripcion/

        Marca al tenant del usuario autenticado como INACTIVO. Solo puede
        ejecutarla un usuario con permiso `editar_mi_negocio` (en la
        practica, el rol Owner del tenant).

        Es una operacion idempotente: si el tenant ya esta inactivo,
        responde con 200 y el mismo estado.
        """
        if not usuario_tiene_permiso(request.user, EDITAR_MI_NEGOCIO):
            return Response(
                {'detail': 'No tienes el permiso necesario para cancelar la suscripcion.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        tenant = request.user.tenant
        if tenant is None:
            return Response(
                {'detail': 'El usuario no pertenece a ningun tenant.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        motivo = (request.data.get('motivo') or '').strip()[:200]

        if tenant.estado == Tenant.Estado.INACTIVO:
            return Response({
                'detail':                'La suscripcion ya estaba cancelada.',
                'tenant_id':             str(tenant.id),
                'estado':                tenant.estado,
                'fecha_vencimiento':     tenant.fecha_vencimiento,
            })

        tenant.estado = Tenant.Estado.INACTIVO
        tenant.save(update_fields=['estado'])

        return Response({
            'detail':                'Suscripcion cancelada correctamente.',
            'tenant_id':             str(tenant.id),
            'estado':                tenant.estado,
            'fecha_vencimiento':     tenant.fecha_vencimiento,
            'fecha_cancelacion':     timezone.localtime(),
            'motivo':                motivo or None,
        })


class TenantModuloViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TenantModuloSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return TenantModulo.objects.filter(
            tenant=self.request.user.tenant,
            activo=True
        )
