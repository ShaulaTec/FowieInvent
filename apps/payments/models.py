from django.conf import settings
from django.db import models


class Plan(models.Model):
    """
    Representa un producto/precio de Stripe almacenado localmente.
    Al crear o actualizar un Plan se sincroniza automáticamente con Stripe
    via el servicio PlanService.
    """

    class Interval(models.TextChoices):
        DAY = "day", "Diario"
        WEEK = "week", "Semanal"
        MONTH = "month", "Mensual"
        YEAR = "year", "Anual"

    # Identificadores Stripe (se rellenan al sincronizar)
    stripe_product_id = models.CharField(max_length=100, blank=True)
    stripe_price_id = models.CharField(max_length=100, blank=True)

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    # Precio en centavos (ej. 999 = $9.99 MXN)
    amount = models.PositiveIntegerField(help_text="Precio en centavos")
    currency = models.CharField(max_length=3, default="mxn")
    interval = models.CharField(
        max_length=10,
        choices=Interval.choices,
        null=True,
        blank=True,
        help_text="Nulo = pago único, con valor = suscripción",
    )
    interval_count = models.PositiveSmallIntegerField(
        default=1,
        help_text="Cada cuántos intervalos se cobra (ej. 3 meses = interval=month, interval_count=3)",
    )
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "payments_plans"
        ordering = ["amount"]

    def __str__(self):
        interval_label = f"/{self.interval}" if self.interval else " (único)"
        return f"{self.name} — {self.amount / 100:.2f} {self.currency.upper()}{interval_label}"

    @property
    def is_recurring(self):
        return bool(self.interval)

    @property
    def amount_display(self):
        return self.amount / 100


class Payment(models.Model):
    """
    Registro de un pago único (PaymentIntent de Stripe).
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pendiente"
        SUCCEEDED = "succeeded", "Exitoso"
        FAILED = "failed", "Fallido"
        CANCELED = "canceled", "Cancelado"
        REFUNDED = "refunded", "Reembolsado"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="payments",
    )
    plan = models.ForeignKey(
        Plan,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payments",
    )
    stripe_payment_intent_id = models.CharField(max_length=200, unique=True)
    stripe_customer_id = models.CharField(max_length=200, blank=True)
    amount = models.PositiveIntegerField(help_text="Monto cobrado en centavos")
    currency = models.CharField(max_length=3, default="mxn")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    description = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "payments_payments"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Payment {self.stripe_payment_intent_id} — {self.status}"


class Subscription(models.Model):
    """
    Registro de una suscripción de Stripe.
    """

    class Status(models.TextChoices):
        ACTIVE = "active", "Activa"
        PAST_DUE = "past_due", "Pago vencido"
        UNPAID = "unpaid", "Sin pagar"
        CANCELED = "canceled", "Cancelada"
        INCOMPLETE = "incomplete", "Incompleta"
        TRIALING = "trialing", "En prueba"
        PAUSED = "paused", "Pausada"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="subscriptions",
    )
    plan = models.ForeignKey(
        Plan,
        on_delete=models.SET_NULL,
        null=True,
        related_name="subscriptions",
    )
    stripe_subscription_id = models.CharField(max_length=200, unique=True)
    stripe_customer_id = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.INCOMPLETE)
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(default=False)
    canceled_at = models.DateTimeField(null=True, blank=True)
    trial_end = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "payments_subscriptions"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Subscription {self.stripe_subscription_id} — {self.status}"

    @property
    def is_active(self):
        return self.status in (self.Status.ACTIVE, self.Status.TRIALING)


class Refund(models.Model):
    """
    Registro de un reembolso aplicado a un Payment.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pendiente"
        SUCCEEDED = "succeeded", "Exitoso"
        FAILED = "failed", "Fallido"
        CANCELED = "canceled", "Cancelado"

    class Reason(models.TextChoices):
        DUPLICATE = "duplicate", "Duplicado"
        FRAUDULENT = "fraudulent", "Fraudulento"
        REQUESTED_BY_CUSTOMER = "requested_by_customer", "Solicitado por cliente"

    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name="refunds")
    stripe_refund_id = models.CharField(max_length=200, unique=True)
    amount = models.PositiveIntegerField(help_text="Monto reembolsado en centavos")
    currency = models.CharField(max_length=3, default="mxn")
    reason = models.CharField(
        max_length=30,
        choices=Reason.choices,
        default=Reason.REQUESTED_BY_CUSTOMER,
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "payments_refunds"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Refund {self.stripe_refund_id} — {self.amount / 100:.2f} {self.currency.upper()}"
