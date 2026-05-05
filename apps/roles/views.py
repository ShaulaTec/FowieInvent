# apps/roles/views.py
from rest_framework import viewsets, permissions
from .models import Permiso, Rol, RolPermiso
from .serializers import PermisoSerializer, RolSerializer, RolPermisoSerializer

class PermisoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Permiso.objects.all()
    serializer_class = PermisoSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        modulos_activos = self.request.user.tenant.modulos.filter(
            activo=True
        ).values_list('modulo__codigo', flat=True)
        return Permiso.objects.filter(modulo__in=modulos_activos)

class RolViewSet(viewsets.ModelViewSet):
    serializer_class = RolSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Rol.objects.filter(
            tenant=self.request.user.tenant,
            activo=True
        )

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.tenant)

class RolPermisoViewSet(viewsets.ModelViewSet):
    serializer_class = RolPermisoSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return RolPermiso.objects.filter(
            rol__tenant=self.request.user.tenant
        )