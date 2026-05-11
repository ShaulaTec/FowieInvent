# apps/inventory/views.py
from rest_framework import viewsets, mixins, permissions
from apps.roles.permissions import PermisoRequeridoMixin
from apps.roles.permisos import (
    VER_INVENTARIO,
    EDITAR_PRODUCTO,
    ELIMINAR_PRODUCTO,
    REGISTRAR_MOVIMIENTO,
    VER_HISTORIAL,
    GESTIONAR_CATEGORIAS,
)
from .models import Categoria, Producto, Movimiento
from .serializers import CategoriaSerializer, ProductoSerializer, MovimientoSerializer


class CategoriaViewSet(PermisoRequeridoMixin, viewsets.ModelViewSet):
    serializer_class = CategoriaSerializer
    permission_classes = [permissions.IsAuthenticated]
    permiso_requerido_map = {
        'list':           VER_INVENTARIO,
        'retrieve':       VER_INVENTARIO,
        'create':         GESTIONAR_CATEGORIAS,
        'update':         GESTIONAR_CATEGORIAS,
        'partial_update': GESTIONAR_CATEGORIAS,
        'destroy':        GESTIONAR_CATEGORIAS,
    }

    def get_queryset(self):
        return Categoria.objects.filter(
            tenant=self.request.user.tenant,
            activo=True
        )

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.tenant)


class ProductoViewSet(PermisoRequeridoMixin, viewsets.ModelViewSet):
    serializer_class = ProductoSerializer
    permission_classes = [permissions.IsAuthenticated]
    permiso_requerido_map = {
        'list':           VER_INVENTARIO,
        'retrieve':       VER_INVENTARIO,
        'create':         EDITAR_PRODUCTO,
        'update':         EDITAR_PRODUCTO,
        'partial_update': EDITAR_PRODUCTO,
        'destroy':        ELIMINAR_PRODUCTO,
    }

    def get_queryset(self):
        return Producto.objects.filter(
            tenant=self.request.user.tenant,
            activo=True
        )

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.tenant)


class MovimientoViewSet(PermisoRequeridoMixin,
                        mixins.CreateModelMixin,
                        mixins.ListModelMixin,
                        mixins.RetrieveModelMixin,
                        viewsets.GenericViewSet):
    serializer_class = MovimientoSerializer
    permission_classes = [permissions.IsAuthenticated]
    permiso_requerido_map = {
        'list':     VER_HISTORIAL,
        'retrieve': VER_HISTORIAL,
        'create':   REGISTRAR_MOVIMIENTO,
    }

    def get_queryset(self):
        return Movimiento.objects.filter(
            producto__tenant=self.request.user.tenant
        )

    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user)
