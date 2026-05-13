# apps/inventory/serializers.py
from rest_framework import serializers
from .models import Categoria, Producto, Movimiento

class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = '__all__'
        read_only_fields = ('tenant',)

class ProductoSerializer(serializers.ModelSerializer):
    categoria = CategoriaSerializer(read_only=True)
    categoria_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = Producto
        fields = '__all__'
        read_only_fields = ('tenant', 'created_at')

class MovimientoSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    usuario_nombre  = serializers.SerializerMethodField()

    class Meta:
        model = Movimiento
        fields = '__all__'
        read_only_fields = ('usuario', 'fecha')

    def get_usuario_nombre(self, obj):
        return obj.usuario.get_username() or obj.usuario.email
