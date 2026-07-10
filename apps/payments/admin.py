from django.contrib import admin

from .models import Payment, Plan, Refund, Subscription


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ["name", "amount_display", "currency", "interval", "is_active", "stripe_price_id"]
    list_filter = ["is_active", "interval", "currency"]
    search_fields = ["name", "stripe_product_id", "stripe_price_id"]
    readonly_fields = ["stripe_product_id", "stripe_price_id", "created_at", "updated_at"]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["stripe_payment_intent_id", "user", "plan", "amount", "currency", "status", "paid_at"]
    list_filter = ["status", "currency"]
    search_fields = ["stripe_payment_intent_id", "stripe_customer_id", "user__email"]
    readonly_fields = ["stripe_payment_intent_id", "stripe_customer_id", "created_at", "updated_at"]


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = [
        "stripe_subscription_id", "user", "plan", "status",
        "current_period_end", "cancel_at_period_end",
    ]
    list_filter = ["status"]
    search_fields = ["stripe_subscription_id", "stripe_customer_id", "user__email"]
    readonly_fields = [
        "stripe_subscription_id", "stripe_customer_id",
        "current_period_start", "current_period_end", "created_at", "updated_at",
    ]


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = ["stripe_refund_id", "payment", "amount", "currency", "reason", "status"]
    list_filter = ["status", "reason"]
    search_fields = ["stripe_refund_id", "payment__stripe_payment_intent_id"]
    readonly_fields = ["stripe_refund_id", "created_at", "updated_at"]
