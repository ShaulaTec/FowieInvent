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
    class Meta:
        model = Movimiento
        fields = '__all__'
        read_only_fields = ('usuario', 'fecha')