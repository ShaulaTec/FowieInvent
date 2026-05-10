from rest_framework import viewsets, permissions
from rest_framework.exceptions import ValidationError
from .models import Categoria, Producto, Movimiento
from .serializers import CategoriaSerializer, ProductoSerializer, MovimientoSerializer


class CategoriaViewSet(viewsets.ModelViewSet):
    serializer_class = CategoriaSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Categoria.objects.filter(tenant=self.request.user.tenant)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.tenant)

    def perform_destroy(self, instance):
        instance.productos.update(activo=False)
        instance.activo = False
        instance.save()


class ProductoViewSet(viewsets.ModelViewSet):
    serializer_class = ProductoSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Producto.objects.filter(tenant=self.request.user.tenant)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.tenant)

    def perform_destroy(self, instance):
        instance.activo = False
        instance.save()


class MovimientoViewSet(viewsets.ModelViewSet):
    serializer_class = MovimientoSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Movimiento.objects.filter(
            producto__tenant=self.request.user.tenant
        )
        producto_id = self.request.query_params.get('producto')
        if producto_id:
            qs = qs.filter(producto__id=producto_id)
        return qs

    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user)
