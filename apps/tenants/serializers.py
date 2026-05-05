# apps/tenants/serializers.py
from rest_framework import serializers
from .models import Plan, Modulo, Tenant, TenantModulo

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