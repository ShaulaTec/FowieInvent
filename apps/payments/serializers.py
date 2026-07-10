from rest_framework import serializers

from .models import Payment, Plan, Refund, Subscription


# ─────────────────────────────────────────────
# Plan
# ─────────────────────────────────────────────

class PlanSerializer(serializers.ModelSerializer):
    amount_display = serializers.ReadOnlyField()
    is_recurring = serializers.ReadOnlyField()

    class Meta:
        model = Plan
        fields = [
            "id", "name", "description", "amount", "amount_display",
            "currency", "interval", "interval_count", "is_recurring",
            "is_active", "stripe_product_id", "stripe_price_id",
            "metadata", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "stripe_product_id", "stripe_price_id", "created_at", "updated_at"]


class PlanWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = [
            "name", "description", "amount", "currency",
            "interval", "interval_count", "is_active", "metadata",
        ]

    def validate(self, attrs):
        interval = attrs.get("interval") or (self.instance.interval if self.instance else None)
        interval_count = attrs.get("interval_count", 1)
        if interval and interval_count < 1:
            raise serializers.ValidationError({"interval_count": "Debe ser al menos 1."})
        return attrs


# ─────────────────────────────────────────────
# Payment
# ─────────────────────────────────────────────

class PaymentSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source="user.email", read_only=True)
    plan_name = serializers.CharField(source="plan.name", read_only=True)
    amount_display = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = [
            "id", "user_email", "plan_name",
            "stripe_payment_intent_id", "stripe_customer_id",
            "amount", "amount_display", "currency", "status",
            "description", "metadata", "paid_at",
            "created_at", "updated_at",
        ]
        read_only_fields = fields

    def get_amount_display(self, obj):
        return obj.amount / 100


class CreatePaymentIntentSerializer(serializers.Serializer):
    plan_id = serializers.PrimaryKeyRelatedField(queryset=Plan.objects.filter(is_active=True))
    payment_method_id = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="ID del método de pago de Stripe (pm_xxx). Opcional: si se envía, el pago se confirma de inmediato.",
    )

    def validate_plan_id(self, plan):
        if plan.is_recurring:
            raise serializers.ValidationError("Este plan es recurrente; usa el endpoint de suscripciones.")
        return plan


class ConfirmPaymentSerializer(serializers.Serializer):
    payment_method_id = serializers.CharField()


# ─────────────────────────────────────────────
# Subscription
# ─────────────────────────────────────────────

class SubscriptionSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source="user.email", read_only=True)
    plan_name = serializers.CharField(source="plan.name", read_only=True)
    is_active = serializers.ReadOnlyField()

    class Meta:
        model = Subscription
        fields = [
            "id", "user_email", "plan_name",
            "stripe_subscription_id", "stripe_customer_id",
            "status", "is_active",
            "current_period_start", "current_period_end",
            "cancel_at_period_end", "canceled_at", "trial_end",
            "metadata", "created_at", "updated_at",
        ]
        read_only_fields = fields


class CreateSubscriptionSerializer(serializers.Serializer):
    plan_id = serializers.PrimaryKeyRelatedField(queryset=Plan.objects.filter(is_active=True))
    payment_method_id = serializers.CharField(
        help_text="ID del método de pago (pm_xxx) a usar para la suscripción."
    )

    def validate_plan_id(self, plan):
        if not plan.is_recurring:
            raise serializers.ValidationError("Este plan no es recurrente; usa el endpoint de pago único.")
        if not plan.stripe_price_id:
            raise serializers.ValidationError("El plan no está sincronizado con Stripe.")
        return plan


class ChangePlanSerializer(serializers.Serializer):
    new_plan_id = serializers.PrimaryKeyRelatedField(
        queryset=Plan.objects.filter(is_active=True),
        help_text="ID del nuevo plan al que se quiere migrar.",
    )

    def validate_new_plan_id(self, plan):
        if not plan.is_recurring:
            raise serializers.ValidationError("El nuevo plan debe ser recurrente.")
        if not plan.stripe_price_id:
            raise serializers.ValidationError("El nuevo plan no está sincronizado con Stripe.")
        return plan


# ─────────────────────────────────────────────
# Refund
# ─────────────────────────────────────────────

class RefundSerializer(serializers.ModelSerializer):
    amount_display = serializers.SerializerMethodField()
    payment_intent_id = serializers.CharField(source="payment.stripe_payment_intent_id", read_only=True)

    class Meta:
        model = Refund
        fields = [
            "id", "payment_intent_id",
            "stripe_refund_id", "amount", "amount_display",
            "currency", "reason", "status", "notes",
            "created_at", "updated_at",
        ]
        read_only_fields = fields

    def get_amount_display(self, obj):
        return obj.amount / 100


class CreateRefundSerializer(serializers.Serializer):
    payment_id = serializers.PrimaryKeyRelatedField(
        queryset=Payment.objects.filter(status=Payment.Status.SUCCEEDED)
    )
    amount = serializers.IntegerField(
        required=False,
        min_value=1,
        help_text="Monto a reembolsar en centavos. Si no se envía, se reembolsa el total.",
    )
    reason = serializers.ChoiceField(
        choices=Refund.Reason.choices,
        default=Refund.Reason.REQUESTED_BY_CUSTOMER,
    )
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        payment = attrs["payment_id"]
        amount = attrs.get("amount")
        if amount and amount > payment.amount:
            raise serializers.ValidationError(
                {"amount": f"El monto no puede superar el pago original ({payment.amount} centavos)."}
            )
        return attrs
