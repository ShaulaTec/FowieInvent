# apps/users/serializers.py
from rest_framework import serializers
from .models import Usuario
from apps.roles.serializers import RolSerializer

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