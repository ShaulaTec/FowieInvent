from rest_framework import serializers
from .models import Plan, Modulo, Tenant, TenantModulo
from apps.payments.serializers import PlanSerializer as BillingPlanSerializer

class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = '__all__'

class ModuloSerializer(serializers.ModelSerializer):
    class Meta:
        model = Modulo
        fields = '__all__'

class TenantSerializer(serializers.ModelSerializer):
    plan = PlanSerializer(read_only=True)
    plan_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = Tenant
        fields = '__all__'

class TenantModuloSerializer(serializers.ModelSerializer):
    modulo = ModuloSerializer(read_only=True)

    class Meta:
        model = TenantModulo
        fields = '__all__'


class TenantPlanSerializer(serializers.ModelSerializer):
    billing_plan = BillingPlanSerializer(read_only=True)
    requiere_pago = serializers.SerializerMethodField()

    class Meta:
        model = Plan
        fields = (
            'id', 'nombre', 'max_usuarios', 'max_productos', 'max_categorias',
            'precio_mensual', 'activo', 'billing_plan', 'requiere_pago',
        )

    def get_requiere_pago(self, obj):
        return obj.billing_plan is not None