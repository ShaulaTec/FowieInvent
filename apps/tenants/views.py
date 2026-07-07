from django.utils import timezone
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from apps.roles.permissions import PermisoRequeridoMixin
from apps.roles.permisos import EDITAR_MI_NEGOCIO, VER_MI_NEGOCIO
from apps.payments.models import Subscription
from apps.payments.services import SubscriptionService
from .models import Plan, Modulo, Tenant, TenantModulo
from .serializers import (
    PlanSerializer,
    TenantPlanSerializer,
    ModuloSerializer,
    TenantSerializer,
    TenantModuloSerializer,
)


class PlanViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Plan.objects.filter(activo=True)
    serializer_class = TenantPlanSerializer
    permission_classes = [permissions.AllowAny]


class ModuloViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Modulo.objects.filter(activo=True)
    serializer_class = ModuloSerializer
    permission_classes = [permissions.IsAuthenticated]


class TenantViewSet(PermisoRequeridoMixin, viewsets.ModelViewSet):
    serializer_class = TenantSerializer
    permission_classes = [permissions.IsAuthenticated]
    permiso_requerido_map = {
        'list': VER_MI_NEGOCIO,
        'retrieve': VER_MI_NEGOCIO,
        'update': EDITAR_MI_NEGOCIO,
        'partial_update': EDITAR_MI_NEGOCIO,
        # `destroy` queda fuera del mapa: la baja se hace via la accion
        # `cancelar_suscripcion`, protegida aparte con chequeo de Owner.
    }

    def get_queryset(self):
        return Tenant.objects.filter(id=self.request.user.tenant.id)

    @action(detail=False, methods=['post'], url_path='cancelar-suscripcion')
    def cancelar_suscripcion(self, request):
        """
        POST /api/tenants/info/cancelar-suscripcion/

        Solo el rol 'Owner' del tenant puede ejecutar esta accion —
        chequeo explicito por nombre de rol, independiente de que
        el tenant le haya asignado `editar_mi_negocio` a otro rol.

        Comportamiento:
          - Plan gratuito (sin billing_plan): se marca INACTIVO de inmediato.
          - Plan de paga: se agenda `cancel_at_period_end=True` en Stripe.
            El tenant SIGUE ACTIVO hasta que termine el periodo ya pagado;
            el webhook `customer.subscription.deleted` marca INACTIVO
            cuando Stripe confirma el corte real.

        Es idempotente: si el tenant ya esta inactivo, o si ya hay una
        cancelacion agendada, responde 200 sin duplicar la operacion.
        """
        usuario = request.user
        rol = getattr(usuario, 'rol', None)

        if rol is None or rol.nombre != 'Owner':
            raise PermissionDenied(
                'Solo el propietario (Owner) del negocio puede cancelar la suscripcion.'
            )

        tenant = usuario.tenant
        if tenant is None:
            return Response(
                {'detail': 'El usuario no pertenece a ningun tenant.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        motivo = (request.data.get('motivo') or '').strip()[:200]

        if tenant.estado == Tenant.Estado.INACTIVO:
            return Response({
                'detail': 'La suscripcion ya estaba cancelada.',
                'tenant_id': str(tenant.id),
                'estado': tenant.estado,
                'fecha_vencimiento': tenant.fecha_vencimiento,
            })

        # ── Plan sin billing (gratuito): corte inmediato ────────────────
        if not tenant.plan.billing_plan:
            tenant.estado = Tenant.Estado.INACTIVO
            tenant.save(update_fields=['estado'])
            return Response({
                'detail': 'Suscripcion cancelada correctamente.',
                'tenant_id': str(tenant.id),
                'estado': tenant.estado,
                'fecha_vencimiento': tenant.fecha_vencimiento,
                'fecha_cancelacion': timezone.localtime(),
                'motivo': motivo or None,
            })

        # ── Plan de paga: agendar cancelacion al final del periodo ──────
        subscription = (
            Subscription.objects
            .filter(user__tenant=tenant, status__in=['active', 'trialing', 'past_due'])
            .order_by('-created_at')
            .first()
        )

        if subscription is None:
            return Response(
                {'detail': 'No se encontro una suscripcion activa en Stripe para este tenant.'},
                status=status.HTTP_409_CONFLICT,
            )

        if subscription.cancel_at_period_end:
            return Response({
                'detail': 'La cancelacion ya estaba agendada para el final del periodo.',
                'tenant_id': str(tenant.id),
                'estado': tenant.estado,
                'acceso_hasta': subscription.current_period_end,
            })

        try:
            subscription = SubscriptionService.cancel_subscription(
                subscription, at_period_end=True
            )
        except Exception as exc:
            return Response(
                {'detail': f'No se pudo agendar la cancelacion en Stripe: {exc}'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response({
            'detail': 'Cancelacion agendada. El acceso continua hasta el final del periodo ya pagado.',
            'tenant_id': str(tenant.id),
            'estado': tenant.estado,  # sigue ACTIVO a proposito
            'acceso_hasta': subscription.current_period_end,
            'fecha_solicitud': timezone.localtime(),
            'motivo': motivo or None,
        })


class TenantModuloViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TenantModuloSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return TenantModulo.objects.filter(
            tenant=self.request.user.tenant,
            activo=True
        )