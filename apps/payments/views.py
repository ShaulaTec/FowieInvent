from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from rbac.permissions import IsSuperUserOrReadOnly

from .models import Payment, Plan, Refund, Subscription
from .serializers import (
    ChangePlanSerializer,
    ConfirmPaymentSerializer,
    CreatePaymentIntentSerializer,
    CreateRefundSerializer,
    CreateSubscriptionSerializer,
    PaymentSerializer,
    PlanSerializer,
    PlanWriteSerializer,
    RefundSerializer,
    SubscriptionSerializer,
)
from .services import PaymentService, PlanService, RefundService, SubscriptionService


# ─────────────────────────────────────────────
# Plan ViewSet  —  /api/payments/plans/
# ─────────────────────────────────────────────

class PlanViewSet(viewsets.ModelViewSet):
    """
    CRUD de planes. Cada creación/edición se sincroniza automáticamente con Stripe.

    list        GET    /api/payments/plans/
    create      POST   /api/payments/plans/
    retrieve    GET    /api/payments/plans/{id}/
    update      PUT    /api/payments/plans/{id}/
    partial     PATCH  /api/payments/plans/{id}/
    destroy     DELETE /api/payments/plans/{id}/   ← desactiva en Stripe
    sync        POST   /api/payments/plans/{id}/sync/  ← fuerza re-sincronización
    """
    queryset = Plan.objects.all()
    permission_classes = [IsAuthenticated, IsSuperUserOrReadOnly]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return PlanWriteSerializer
        return PlanSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        is_active = self.request.query_params.get("is_active")
        interval = self.request.query_params.get("interval")
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == "true")
        if interval:
            qs = qs.filter(interval=interval) if interval != "one_time" else qs.filter(interval__isnull=True)
        return qs

    def perform_create(self, serializer):
        plan = serializer.save()
        PlanService.sync_to_stripe(plan)

    def perform_update(self, serializer):
        plan = serializer.save()
        PlanService.sync_to_stripe(plan)

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active"])
        PlanService.deactivate_in_stripe(instance)

    @action(detail=True, methods=["post"], url_path="sync")
    def sync(self, request, pk=None):
        """Fuerza la re-sincronización del plan con Stripe."""
        plan = self.get_object()
        PlanService.sync_to_stripe(plan)
        return Response(PlanSerializer(plan).data)


# ─────────────────────────────────────────────
# Payment ViewSet  —  /api/payments/payments/
# ─────────────────────────────────────────────

class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Historial de pagos (solo lectura). La creación es vía /create-intent/.

    list        GET    /api/payments/payments/
    retrieve    GET    /api/payments/payments/{id}/

    Acciones:
    create-intent  POST   /api/payments/create-intent/          ← crea PaymentIntent
    confirm        POST   /api/payments/{id}/confirm/           ← confirma pago
    cancel         POST   /api/payments/{id}/cancel/            ← cancela PaymentIntent
    refund         POST   /api/payments/{id}/refund/            ← reembolsa pago
    my-payments    GET    /api/payments/payments/my/            ← pagos del usuario autenticado
    """
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Payment.objects.select_related("user", "plan").all()
        # Superusuarios ven todo; usuarios normales solo sus propios pagos
        if not user.is_superuser:
            qs = qs.filter(user=user)
        status_filter = self.request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs

    @action(detail=False, methods=["post"], url_path="create-intent")
    def create_intent(self, request):
        """Crea un PaymentIntent en Stripe."""
        serializer = CreatePaymentIntentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        plan = serializer.validated_data["plan_id"]
        payment_method_id = serializer.validated_data.get("payment_method_id")

        payment = PaymentService.create_payment_intent(
            user=request.user,
            plan=plan,
            payment_method_id=payment_method_id or None,
        )
        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="confirm")
    def confirm(self, request, pk=None):
        """Confirma un PaymentIntent pendiente con un método de pago."""
        payment = self.get_object()
        serializer = ConfirmPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        payment = PaymentService.confirm_payment_intent(
            payment=payment,
            payment_method_id=serializer.validated_data["payment_method_id"],
        )
        return Response(PaymentSerializer(payment).data)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        """Cancela un PaymentIntent que no ha sido confirmado."""
        payment = self.get_object()
        if payment.status != Payment.Status.PENDING:
            return Response(
                {"detail": "Solo se pueden cancelar pagos en estado 'pending'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        payment = PaymentService.cancel_payment_intent(payment)
        return Response(PaymentSerializer(payment).data)

    @action(detail=True, methods=["post"], url_path="refund")
    def refund(self, request, pk=None):
        """Crea un reembolso (total o parcial) para un pago exitoso."""
        payment = self.get_object()
        serializer = CreateRefundSerializer(data={**request.data, "payment_id": payment.pk})
        serializer.is_valid(raise_exception=True)

        refund = RefundService.create_refund(
            payment=payment,
            amount=serializer.validated_data.get("amount"),
            reason=serializer.validated_data["reason"],
        )
        return Response(RefundSerializer(refund).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"], url_path="my")
    def my_payments(self, request):
        """Devuelve los pagos del usuario autenticado."""
        payments = Payment.objects.filter(user=request.user).select_related("plan")
        serializer = PaymentSerializer(payments, many=True)
        return Response(serializer.data)


# ─────────────────────────────────────────────
# Subscription ViewSet  —  /api/payments/subscriptions/
# ─────────────────────────────────────────────

class SubscriptionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Historial de suscripciones (solo lectura). La creación es vía /subscribe/.

    list        GET    /api/payments/subscriptions/
    retrieve    GET    /api/payments/subscriptions/{id}/

    Acciones:
    subscribe    POST   /api/payments/subscriptions/subscribe/          ← nueva suscripción
    cancel       POST   /api/payments/subscriptions/{id}/cancel/        ← cancelar
    change-plan  POST   /api/payments/subscriptions/{id}/change-plan/   ← cambiar plan
    pause        POST   /api/payments/subscriptions/{id}/pause/         ← pausar
    resume       POST   /api/payments/subscriptions/{id}/resume/        ← reanudar
    my           GET    /api/payments/subscriptions/my/                 ← mis suscripciones
    """
    serializer_class = SubscriptionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Subscription.objects.select_related("user", "plan").all()
        if not user.is_superuser:
            qs = qs.filter(user=user)
        status_filter = self.request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs

    @action(detail=False, methods=["post"], url_path="subscribe")
    def subscribe(self, request):
        """Crea una nueva suscripción en Stripe."""
        serializer = CreateSubscriptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        subscription = SubscriptionService.create_subscription(
            user=request.user,
            plan=serializer.validated_data["plan_id"],
            payment_method_id=serializer.validated_data["payment_method_id"],
        )
        return Response(SubscriptionSerializer(subscription).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        """Cancela la suscripción. at_period_end=true (default) o false para cancelación inmediata."""
        subscription = self.get_object()
        at_period_end = request.data.get("at_period_end", True)
        subscription = SubscriptionService.cancel_subscription(subscription, at_period_end=at_period_end)
        return Response(SubscriptionSerializer(subscription).data)

    @action(detail=True, methods=["post"], url_path="change-plan")
    def change_plan(self, request, pk=None):
        """Migra la suscripción a un nuevo plan con prorrateo automático."""
        subscription = self.get_object()
        serializer = ChangePlanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        subscription = SubscriptionService.change_plan(
            subscription=subscription,
            new_plan=serializer.validated_data["new_plan_id"],
        )
        return Response(SubscriptionSerializer(subscription).data)

    @action(detail=True, methods=["post"], url_path="pause")
    def pause(self, request, pk=None):
        """Pausa la recaudación de la suscripción."""
        subscription = self.get_object()
        subscription = SubscriptionService.pause_subscription(subscription)
        return Response(SubscriptionSerializer(subscription).data)

    @action(detail=True, methods=["post"], url_path="resume")
    def resume(self, request, pk=None):
        """Reanuda una suscripción pausada."""
        subscription = self.get_object()
        subscription = SubscriptionService.resume_subscription(subscription)
        return Response(SubscriptionSerializer(subscription).data)

    @action(detail=False, methods=["get"], url_path="my")
    def my_subscriptions(self, request):
        """Devuelve las suscripciones del usuario autenticado."""
        subs = Subscription.objects.filter(user=request.user).select_related("plan")
        return Response(SubscriptionSerializer(subs, many=True).data)


# ─────────────────────────────────────────────
# Refund ViewSet  —  /api/payments/refunds/
# ─────────────────────────────────────────────

class RefundViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Historial de reembolsos (solo lectura).
    La creación se hace desde POST /api/payments/payments/{id}/refund/.

    list        GET    /api/payments/refunds/
    retrieve    GET    /api/payments/refunds/{id}/
    """
    serializer_class = RefundSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Refund.objects.select_related("payment__user").all()
        if not user.is_superuser:
            qs = qs.filter(payment__user=user)
        return qs
