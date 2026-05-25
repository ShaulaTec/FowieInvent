"""
Manejador de Webhooks de Stripe.

Stripe envía eventos firmados a /api/payments/webhook/.
Este módulo verifica la firma y despacha cada evento al handler correcto.

Eventos soportados:
  payment_intent.succeeded          → marca Payment como succeeded
  payment_intent.payment_failed     → marca Payment como failed
  customer.subscription.updated     → actualiza estado de Subscription
  customer.subscription.deleted     → cancela Subscription localmente
  invoice.paid                      → registra pago de factura de suscripción
  invoice.payment_failed            → marca suscripción como past_due
  charge.refunded                   → actualiza estado del Refund
"""
import logging
from datetime import datetime, timezone

import stripe
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response

from .models import Payment, Refund, Subscription

logger = logging.getLogger(__name__)


def _ts(timestamp):
    if timestamp is None:
        return None
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)


# ─────────────────────────────────────────────
# Endpoint principal
# ─────────────────────────────────────────────

@csrf_exempt
@api_view(["POST"])
@authentication_classes([])   # Sin autenticación JWT: Stripe firma con su propio header
@permission_classes([])
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        logger.warning("Webhook: payload inválido.")
        return Response({"detail": "Payload inválido."}, status=status.HTTP_400_BAD_REQUEST)
    except stripe.error.SignatureVerificationError:
        logger.warning("Webhook: firma inválida.")
        return Response({"detail": "Firma inválida."}, status=status.HTTP_400_BAD_REQUEST)

    event_type = event["type"]
    data = event["data"]["object"]

    logger.info("Webhook recibido: %s (id=%s)", event_type, event["id"])

    handlers = {
        "payment_intent.succeeded": _handle_payment_intent_succeeded,
        "payment_intent.payment_failed": _handle_payment_intent_failed,
        "customer.subscription.updated": _handle_subscription_updated,
        "customer.subscription.deleted": _handle_subscription_deleted,
        "invoice.paid": _handle_invoice_paid,
        "invoice.payment_failed": _handle_invoice_payment_failed,
        "charge.refunded": _handle_charge_refunded,
    }

    handler = handlers.get(event_type)
    if handler:
        try:
            handler(data)
        except Exception as exc:
            logger.error("Error en handler %s: %s", event_type, exc, exc_info=True)
            # Retornamos 200 para que Stripe no reintente; el error se loggea
    else:
        logger.debug("Evento no manejado: %s", event_type)

    return Response({"received": True})


# ─────────────────────────────────────────────
# Handlers de eventos
# ─────────────────────────────────────────────

def _handle_payment_intent_succeeded(intent):
    """Marca el Payment local como exitoso."""
    try:
        payment = Payment.objects.get(stripe_payment_intent_id=intent["id"])
    except Payment.DoesNotExist:
        logger.warning("PaymentIntent %s no encontrado localmente.", intent["id"])
        return

    payment.status = Payment.Status.SUCCEEDED
    payment.paid_at = datetime.now(tz=timezone.utc)
    payment.save(update_fields=["status", "paid_at"])
    logger.info("Payment %s marcado como succeeded.", payment.pk)


def _handle_payment_intent_failed(intent):
    """Marca el Payment local como fallido."""
    try:
        payment = Payment.objects.get(stripe_payment_intent_id=intent["id"])
    except Payment.DoesNotExist:
        logger.warning("PaymentIntent %s no encontrado localmente.", intent["id"])
        return

    payment.status = Payment.Status.FAILED
    payment.save(update_fields=["status"])
    logger.info("Payment %s marcado como failed.", payment.pk)


def _handle_subscription_updated(stripe_sub):
    """Actualiza el estado y fechas de una Subscription."""
    try:
        sub = Subscription.objects.get(stripe_subscription_id=stripe_sub["id"])
    except Subscription.DoesNotExist:
        logger.warning("Subscription %s no encontrada localmente.", stripe_sub["id"])
        return

    sub.status = stripe_sub["status"]
    sub.current_period_start = _ts(stripe_sub.get("current_period_start"))
    sub.current_period_end = _ts(stripe_sub.get("current_period_end"))
    sub.cancel_at_period_end = stripe_sub.get("cancel_at_period_end", False)
    sub.trial_end = _ts(stripe_sub.get("trial_end"))
    sub.save(update_fields=[
        "status", "current_period_start", "current_period_end",
        "cancel_at_period_end", "trial_end",
    ])
    logger.info("Subscription %s actualizada a estado '%s'.", sub.pk, sub.status)


def _handle_subscription_deleted(stripe_sub):
    """Marca la Subscription como cancelada."""
    try:
        sub = Subscription.objects.get(stripe_subscription_id=stripe_sub["id"])
    except Subscription.DoesNotExist:
        logger.warning("Subscription %s no encontrada localmente.", stripe_sub["id"])
        return

    sub.status = Subscription.Status.CANCELED
    sub.canceled_at = datetime.now(tz=timezone.utc)
    sub.save(update_fields=["status", "canceled_at"])
    logger.info("Subscription %s cancelada por evento de Stripe.", sub.pk)


def _handle_invoice_paid(invoice):
    """
    Cuando Stripe cobra una factura recurrente con éxito,
    actualizamos las fechas del período de la suscripción.
    """
    stripe_sub_id = invoice.get("subscription")
    if not stripe_sub_id:
        return

    try:
        sub = Subscription.objects.get(stripe_subscription_id=stripe_sub_id)
    except Subscription.DoesNotExist:
        logger.warning("Subscription %s no encontrada (invoice.paid).", stripe_sub_id)
        return

    # Refrescar fechas desde Stripe
    stripe_sub = stripe.Subscription.retrieve(stripe_sub_id)
    sub.status = stripe_sub["status"]
    sub.current_period_start = _ts(stripe_sub.get("current_period_start"))
    sub.current_period_end = _ts(stripe_sub.get("current_period_end"))
    sub.save(update_fields=["status", "current_period_start", "current_period_end"])
    logger.info("Subscription %s renovada (invoice.paid).", sub.pk)


def _handle_invoice_payment_failed(invoice):
    """Marca la suscripción como past_due cuando falla el cobro de la factura."""
    stripe_sub_id = invoice.get("subscription")
    if not stripe_sub_id:
        return

    try:
        sub = Subscription.objects.get(stripe_subscription_id=stripe_sub_id)
    except Subscription.DoesNotExist:
        logger.warning("Subscription %s no encontrada (invoice.payment_failed).", stripe_sub_id)
        return

    sub.status = Subscription.Status.PAST_DUE
    sub.save(update_fields=["status"])
    logger.info("Subscription %s marcada como past_due.", sub.pk)


def _handle_charge_refunded(charge):
    """Actualiza el estado del Refund cuando Stripe lo confirma."""
    for stripe_refund in charge.get("refunds", {}).get("data", []):
        try:
            refund = Refund.objects.get(stripe_refund_id=stripe_refund["id"])
            refund.status = stripe_refund["status"]
            refund.save(update_fields=["status"])
            logger.info("Refund %s actualizado a '%s'.", refund.pk, refund.status)
        except Refund.DoesNotExist:
            logger.warning("Refund %s no encontrado localmente.", stripe_refund["id"])
