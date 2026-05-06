# apps/users/serializers.py
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from .models import Usuario
from apps.roles.models import Rol
from apps.roles.serializers import RolSerializer
from apps.tenants.models import Tenant, Plan


# ── Login: acepta email en lugar de username ──────────────────────────────────

class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = 'email'

    def validate(self, attrs):
        email    = attrs.get('email')
        password = attrs.get('password')

        try:
            user = Usuario.objects.get(email=email)
        except Usuario.DoesNotExist:
            raise serializers.ValidationError('Correo o contraseña incorrectos.')

        if not user.check_password(password):
            raise serializers.ValidationError('Correo o contraseña incorrectos.')

        if not user.activo:
            raise serializers.ValidationError('Esta cuenta está desactivada.')

        refresh = self.get_token(user)
        return {
            'access':  str(refresh.access_token),
            'refresh': str(refresh),
            'user': {
                'id':     str(user.id),
                'email':  user.email,
                'tenant': str(user.tenant.id),
                'rol':    user.rol.nombre,
            }
        }


# ── Usuarios dentro de un tenant ──────────────────────────────────────────────

class UsuarioSerializer(serializers.ModelSerializer):
    rol      = RolSerializer(read_only=True)
    rol_id   = serializers.UUIDField(write_only=True)
    password = serializers.CharField(write_only=True)

    class Meta:
        model  = Usuario
        fields = ('id', 'email', 'rol', 'rol_id', 'activo', 'ultimo_acceso', 'password')
        read_only_fields = ('tenant',)

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = Usuario(**validated_data)
        user.set_password(password)
        user.save()
        return user


# ── Register: Tenant + Rol Owner + Usuario en una transacción ────────────────

class RegisterSerializer(serializers.Serializer):
    nombre         = serializers.CharField(max_length=150)
    apellido       = serializers.CharField(max_length=150)
    email          = serializers.EmailField()
    password       = serializers.CharField(write_only=True, min_length=8)
    nombre_negocio = serializers.CharField(max_length=200)
    plan_id        = serializers.UUIDField(required=False, allow_null=True)

    def validate_email(self, value):
        if Usuario.objects.filter(email=value).exists():
            raise serializers.ValidationError('Ya existe una cuenta con este correo.')
        return value

    @transaction.atomic
    def create(self, validated_data):
        # 1. Resuelve plan
        plan_id = validated_data.get('plan_id')
        if plan_id:
            try:
                plan = Plan.objects.get(id=plan_id, activo=True)
            except Plan.DoesNotExist:
                raise serializers.ValidationError('Plan no encontrado.')
        else:
            plan = Plan.objects.filter(activo=True).first()
            if not plan:
                raise serializers.ValidationError('No hay planes disponibles.')

        # 2. Crea el Tenant
        tenant = Tenant.objects.create(
            nombre_negocio=validated_data['nombre_negocio'],
            email_contacto=validated_data['email'],
            plan=plan,
            fecha_vencimiento=timezone.now().date() + timedelta(days=30),
        )

        # 3. Crea el rol "Owner" para este tenant
        rol_owner = Rol.objects.create(
            tenant=tenant,
            nombre='Owner',
            descripcion='Propietario del negocio — acceso total.',
        )

        # 4. Crea el Usuario owner
        user = Usuario(
            email=validated_data['email'],
            tenant=tenant,
            rol=rol_owner,
        )
        user.set_password(validated_data['password'])
        user.save()

        return user
