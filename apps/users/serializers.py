# apps/users/serializers.py
from rest_framework import serializers
from django.db import transaction
from .models import Usuario
from apps.roles.serializers import RolSerializer
from apps.tenants.models import Tenant, Plan


class UsuarioSerializer(serializers.ModelSerializer):
    rol = RolSerializer(read_only=True)
    rol_id = serializers.UUIDField(write_only=True)
    password = serializers.CharField(write_only=True)

    class Meta:
        model = Usuario
        fields = ('id', 'email', 'rol', 'rol_id', 'activo', 'ultimo_acceso', 'password')
        read_only_fields = ('tenant',)

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = Usuario(**validated_data)
        user.set_password(password)
        user.save()
        return user


class RegisterSerializer(serializers.Serializer):
    # Datos del usuario
    nombre       = serializers.CharField(max_length=150)
    apellido     = serializers.CharField(max_length=150)
    email        = serializers.EmailField()
    password     = serializers.CharField(write_only=True, min_length=8)
    # Datos del tenant
    nombre_negocio = serializers.CharField(max_length=255)
    plan_id        = serializers.UUIDField(required=False, allow_null=True)

    def validate_email(self, value):
        if Usuario.objects.filter(email=value).exists():
            raise serializers.ValidationError('Ya existe una cuenta con este correo.')
        return value

    @transaction.atomic
    def create(self, validated_data):
        # Resuelve plan (usa el primero activo si no se especifica)
        plan_id = validated_data.get('plan_id')
        if plan_id:
            plan = Plan.objects.get(id=plan_id, activo=True)
        else:
            plan = Plan.objects.filter(activo=True).first()
            if not plan:
                raise serializers.ValidationError('No hay planes disponibles.')

        # Crea el Tenant
        tenant = Tenant.objects.create(
            nombre=validated_data['nombre_negocio'],
            plan=plan,
        )

        # Crea el Usuario owner
        user = Usuario(
            email=validated_data['email'],
            first_name=validated_data['nombre'],
            last_name=validated_data['apellido'],
            tenant=tenant,
        )
        user.set_password(validated_data['password'])
        user.save()

        return user
