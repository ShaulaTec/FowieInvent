"""
Capa de servicios para Stripe.
Toda la lógica de comunicación con la API de Stripe vive aquí,
manteniendo las vistas limpias y testables.
"""
from datetime import datetime, timezone

import stripe
from django.conf import settings

from .models import Payment, Plan, Refund, Subscription

stripe.api_key = settings.STRIPE_SECRET_KEY


# ─────────────────────────────────────────────
# Helpers internos
# ─────────────────────────────────────────────

def _get_or_create_customer(user) -> str:
    """
    Retorna el stripe_customer_id del usuario.
    Si no tiene uno, lo crea en Stripe y lo cachea en metadata del primer
    objeto que lo tenga, o lo devuelve directamente.
    """
    # Buscar si ya existe un customer asociado
    existing = (
        Subscription.objects.filter(user=user)
        .exclude(stripe_customer_id="")
        .values_list("stripe_customer_id", flat=True)
        .first()
    ) or (
        Payment.objects.filter(user=user)
        .exclude(stripe_customer_id="")
        .values_list("stripe_customer_id", flat=True)
        .first()
    )
    if existing:
        return existing

    # Crear nuevo customer en Stripe
    customer = stripe.Customer.create(
        email=user.email,
        name=f"{user.first_name} {user.last_name}".strip() or user.email,
        metadata={"user_id": str(user.pk)},
    )
    return customer["id"]


def _ts_to_dt(timestamp):
    """Convierte un Unix timestamp de Stripe a datetime aware."""
    if timestamp is None:
        return None
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)


# ─────────────────────────────────────────────
# PlanService
# ─────────────────────────────────────────────

class PlanService:

    @staticmethod
    def sync_to_stripe(plan: Plan) -> Plan:
        """
        Crea o actualiza el Producto y el Precio en Stripe.
        Siempre crea un nuevo Price cuando cambia el monto/intervalo
        (Stripe no permite editar Prices existentes).
        """
        # 1. Producto
        if plan.stripe_product_id:
            product = stripe.Product.modify(
                plan.stripe_product_id,
                name=plan.name,
                description=plan.description or None,
                active=plan.is_active,
                metadata=plan.metadata,
            )
        else:
            product = stripe.Product.create(
                name=plan.name,
                description=plan.description or None,
                active=plan.is_active,
                metadata={**plan.metadata, "plan_id": str(plan.pk)},
            )
            plan.stripe_product_id = product["id"]

        # 2. Precio
        price_params = dict(
            unit_amount=plan.amount,
            currency=plan.currency,
            product=plan.stripe_product_id,
            metadata={"plan_id": str(plan.pk)},
        )
        if plan.is_recurring:
            price_params["recurring"] = {
                "interval": plan.interval,
                "interval_count": plan.interval_count,
            }

        # Archivar precio anterior si existe
        if plan.stripe_price_id:
            stripe.Price.modify(plan.stripe_price_id, active=False)

        price = stripe.Price.create(**price_params)
        plan.stripe_price_id = price["id"]
        plan.save(update_fields=["stripe_product_id", "stripe_price_id"])
        return plan

    @staticmethod
    def deactivate_in_stripe(plan: Plan):
        """Desactiva el producto y precio en Stripe."""
        if plan.stripe_product_id:
            stripe.Product.modify(plan.stripe_product_id, active=False)
        if plan.stripe_price_id:
            stripe.Price.modify(plan.stripe_price_id, active=False)


# ─────────────────────────────────────────────
# PaymentService  (pagos únicos)
# ─────────────────────────────────────────────

class PaymentService:

    @staticmethod
    def create_payment_intent(user, plan: Plan, payment_method_id: str = None) -> Payment:
        """
        Crea un PaymentIntent en Stripe y guarda el registro local.
        Si se pasa payment_method_id se confirma de inmediato.
        """
        customer_id = _get_or_create_customer(user)

        intent_params = dict(
            amount=plan.amount,
            currency=plan.currency,
            customer=customer_id,
            description=plan.description or plan.name,
            metadata={
                "user_id": str(user.pk),
                "plan_id": str(plan.pk),
            },
        )
        if payment_method_id:
            intent_params["payment_method"] = payment_method_id
            intent_params["confirm"] = True
            intent_params["return_url"] = settings.STRIPE_RETURN_URL

        intent = stripe.PaymentIntent.create(**intent_params)

        payment = Payment.objects.create(
            user=user,
            plan=plan,
            stripe_payment_intent_id=intent["id"],
            stripe_customer_id=customer_id,
            amount=plan.amount,
            currency=plan.currency,
            status=intent["status"]
            if intent["status"] in Payment.Status.values
            else Payment.Status.PENDING,
        )
        return payment

    @staticmethod
    def confirm_payment_intent(payment: Payment, payment_method_id: str) -> Payment:
        """Confirma un PaymentIntent ya creado."""
        intent = stripe.PaymentIntent.confirm(
            payment.stripe_payment_intent_id,
            payment_method=payment_method_id,
            return_url=settings.STRIPE_RETURN_URL,
        )
        payment.status = intent["status"]
        if intent["status"] == "succeeded":
            payment.paid_at = datetime.now(tz=timezone.utc)
        payment.save(update_fields=["status", "paid_at"])
        return payment

    @staticmethod
    def cancel_payment_intent(payment: Payment) -> Payment:
        """Cancela un PaymentIntent que aún no fue confirmado."""
        stripe.PaymentIntent.cancel(payment.stripe_payment_intent_id)
        payment.status = Payment.Status.CANCELED
        payment.save(update_fields=["status"])
        return payment


# ─────────────────────────────────────────────
# SubscriptionService
# ─────────────────────────────────────────────

class SubscriptionService:

    @staticmethod
    def create_subscription(user, plan: Plan, payment_method_id: str) -> Subscription:
        """
        Crea una suscripción en Stripe y registra localmente.
        El payment_method se adjunta al customer como método por defecto.
        """
        if not plan.is_recurring:
            raise ValueError("El plan seleccionado no es recurrente.")
        if not plan.stripe_price_id:
            raise ValueError("El plan no está sincronizado con Stripe. Sincronízalo primero.")

        customer_id = _get_or_create_customer(user)

        # Adjuntar y establecer como método por defecto
        stripe.PaymentMethod.attach(payment_method_id, customer=customer_id)
        stripe.Customer.modify(
            customer_id,
            invoice_settings={"default_payment_method": payment_method_id},
        )

        stripe_sub = stripe.Subscription.create(
            customer=customer_id,
            items=[{"price": plan.stripe_price_id}],
            expand=["latest_invoice.payment_intent"],
            metadata={"user_id": str(user.pk), "plan_id": str(plan.pk)},
        )

        subscription = Subscription.objects.create(
            user=user,
            plan=plan,
            stripe_subscription_id=stripe_sub["id"],
            stripe_customer_id=customer_id,
            status=stripe_sub["status"],
            current_period_start=_ts_to_dt(stripe_sub["current_period_start"]),
            current_period_end=_ts_to_dt(stripe_sub["current_period_end"]),
            cancel_at_period_end=stripe_sub["cancel_at_period_end"],
            trial_end=_ts_to_dt(stripe_sub.get("trial_end")),
        )
        return subscription

    @staticmethod
    def cancel_subscription(subscription: Subscription, at_period_end: bool = True) -> Subscription:
        """
        Cancela la suscripción al final del período (por defecto)
        o de inmediato si at_period_end=False.
        """
        if at_period_end:
            stripe_sub = stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                cancel_at_period_end=True,
            )
            subscription.cancel_at_period_end = True
        else:
            stripe_sub = stripe.Subscription.cancel(subscription.stripe_subscription_id)
            subscription.status = Subscription.Status.CANCELED
            subscription.canceled_at = datetime.now(tz=timezone.utc)

        subscription.save(update_fields=["status", "cancel_at_period_end", "canceled_at"])
        return subscription

    @staticmethod
    def change_plan(subscription: Subscription, new_plan: Plan) -> Subscription:
        """Cambia el plan (precio) de una suscripción activa."""
        if not new_plan.stripe_price_id:
            raise ValueError("El nuevo plan no está sincronizado con Stripe.")

        stripe_sub = stripe.Subscription.retrieve(subscription.stripe_subscription_id)
        item_id = stripe_sub["items"]["data"][0]["id"]

        stripe.Subscription.modify(
            subscription.stripe_subscription_id,
            items=[{"id": item_id, "price": new_plan.stripe_price_id}],
            proration_behavior="always_invoice",
            metadata={"plan_id": str(new_plan.pk)},
        )
        subscription.plan = new_plan
        subscription.save(update_fields=["plan"])
        return subscription

    @staticmethod
    def pause_subscription(subscription: Subscription) -> Subscription:
        """Pausa la recaudación de la suscripción."""
        stripe.Subscription.modify(
            subscription.stripe_subscription_id,
            pause_collection={"behavior": "mark_uncollectible"},
        )
        subscription.status = Subscription.Status.PAUSED
        subscription.save(update_fields=["status"])
        return subscription

    @staticmethod
    def resume_subscription(subscription: Subscription) -> Subscription:
        """Reanuda una suscripción pausada."""
        stripe.Subscription.modify(
            subscription.stripe_subscription_id,
            pause_collection="",
        )
        subscription.status = Subscription.Status.ACTIVE
        subscription.save(update_fields=["status"])
        return subscription


# ─────────────────────────────────────────────
# RefundService
# ─────────────────────────────────────────────

class RefundService:

    @staticmethod
    def create_refund(payment: Payment, amount: int = None, reason: str = "requested_by_customer") -> Refund:
        """
        Crea un reembolso en Stripe.
        - amount=None → reembolso total.
        - amount=int  → reembolso parcial en centavos.
        """
        if payment.status not in (Payment.Status.SUCCEEDED,):
            raise ValueError("Solo se pueden reembolsar pagos con estado 'succeeded'.")

        # Obtener el charge_id del payment intent
        intent = stripe.PaymentIntent.retrieve(payment.stripe_payment_intent_id)
        latest_charge = intent.get("latest_charge")
        if not latest_charge:
            raise ValueError("No se encontró el cargo asociado al pago.")

        refund_params = dict(charge=latest_charge, reason=reason)
        if amount:
            refund_params["amount"] = amount

        stripe_refund = stripe.Refund.create(**refund_params)

        refund_amount = amount or payment.amount
        refund = Refund.objects.create(
            payment=payment,
            stripe_refund_id=stripe_refund["id"],
            amount=refund_amount,
            currency=payment.currency,
            reason=reason,
            status=stripe_refund["status"],
        )

        # Si es reembolso total, actualizar el pago
        if not amount or amount >= payment.amount:
            payment.status = Payment.Status.REFUNDED
            payment.save(update_fields=["status"])

        return refund
