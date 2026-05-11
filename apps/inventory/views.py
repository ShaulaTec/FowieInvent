from rest_framework import viewsets, mixins, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction

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

    @action(detail=True, methods=['post'], url_path='reactivar')
    @transaction.atomic
    def reactivar(self, request, pk=None):
        categoria = self.get_object()
        categoria.activo = True
        categoria.save()
        productos_inactivos = categoria.productos.filter(activo=False)
        return Response({
            'categoria': CategoriaSerializer(categoria).data,
            'productos_inactivos': ProductoSerializer(productos_inactivos, many=True).data,
        })


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

    @action(detail=False, methods=['post'], url_path='activar-batch')
    @transaction.atomic
    def activar_batch(self, request):
        ids = request.data.get('ids', [])
        if not ids:
            return Response(
                {'error': 'No se proporcionaron IDs.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        activados = Producto.objects.filter(
            id__in=ids,
            tenant=request.user.tenant
        ).update(activo=True)
        return Response({'activados': activados})

    @action(detail=True, methods=['post'], url_path='reactivar')
    def reactivar(self, request, pk=None):
        producto = self.get_object()

        if not producto.categoria.activo:
            return Response(
                {'error': 'La categoría de este producto está inactiva. Ve al dashboard de categorías para activarla primero.'},
                status=status.HTTP_409_CONFLICT
            )

        producto.activo = True
        producto.save()
        return Response(ProductoSerializer(producto).data)


class MovimientoViewSet(mixins.CreateModelMixin,
                        mixins.ListModelMixin,
                        mixins.RetrieveModelMixin,
                        viewsets.GenericViewSet):
    serializer_class = MovimientoSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Movimiento.objects.filter(producto__tenant=self.request.user.tenant)
        producto_id = self.request.query_params.get('producto')
        if producto_id:
            qs = qs.filter(producto__id=producto_id)
        return qs

    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user)
