from rest_framework import serializers
from .models import Categoria, Producto, Movimiento
from apps.notifications.models import Notificacion
from drf_extra_fields.fields import Base64ImageField

class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = '__all__'
        read_only_fields = ('tenant',)

    def validate(self, attrs):
        request = self.context.get('request')
        tenant = request.user.tenant
        plan = tenant.plan

        if not self.instance:  # Solo en creación
            if tenant.categorias.count() >= plan.max_categorias:
                raise serializers.ValidationError(
                    {"detail": f"Tu plan solo permite {plan.max_categorias} categorías."}
                )
        return attrs


class ProductoSerializer(serializers.ModelSerializer):
    categoria    = CategoriaSerializer(read_only=True)
    categoria_id = serializers.UUIDField(write_only=True)
    imagen = Base64ImageField(required=False, allow_null=True)
    

    class Meta:
        model = Producto
        fields = '__all__'
        read_only_fields = ('tenant', 'created_at')

    def validate(self, attrs):
        request = self.context.get('request')
        tenant = request.user.tenant
        plan = tenant.plan

        if not self.instance:  # Solo en creación
            if tenant.productos.count() >= plan.max_productos:
                raise serializers.ValidationError(
                    {"detail": f"Tu plan solo permite {plan.max_productos} productos."}
                )
        return attrs
    
    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['tenant'] = request.user.tenant
        return super().create(validated_data)



class MovimientoSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    usuario_nombre  = serializers.SerializerMethodField()

    class Meta:
        model = Movimiento
        fields = '__all__'
        read_only_fields = ('usuario', 'fecha')

    def get_usuario_nombre(self, obj):
        return obj.usuario.get_username() or obj.usuario.email
    
    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['usuario'] = request.user 
    
        return super().create(validated_data)
