# apps/tenants/views.py
from rest_framework import viewsets, permissions
from .models import Plan, Modulo, Tenant, TenantModulo
from .serializers import PlanSerializer, ModuloSerializer, TenantSerializer, TenantModuloSerializer

class PlanViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Plan.objects.filter(activo=True)
    serializer_class = PlanSerializer
    permission_classes = [permissions.IsAuthenticated]

class ModuloViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Modulo.objects.filter(activo=True)
    serializer_class = ModuloSerializer
    permission_classes = [permissions.IsAuthenticated]

class TenantViewSet(viewsets.ModelViewSet):
    serializer_class = TenantSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Tenant.objects.filter(id=self.request.user.tenant.id)

class TenantModuloViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TenantModuloSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return TenantModulo.objects.filter(
            tenant=self.request.user.tenant,
            activo=True
        )