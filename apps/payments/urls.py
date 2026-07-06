from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import PaymentViewSet, PlanViewSet, RefundViewSet, SubscriptionViewSet
from .webhooks import stripe_webhook

router = DefaultRouter()
router.register(r"plans", PlanViewSet, basename="plan")
router.register(r"payments", PaymentViewSet, basename="payment")
router.register(r"subscriptions", SubscriptionViewSet, basename="subscription")
router.register(r"refunds", RefundViewSet, basename="refund")

urlpatterns = [
    # Webhook (fuera del router para evitar el prefijo /api/payments/payments/)
    path("webhook/", stripe_webhook, name="stripe-webhook"),
    *router.urls,
]
