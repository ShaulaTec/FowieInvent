# apps/users/views.py
from rest_framework import viewsets, permissions
from .models import Usuario
from .serializers import UsuarioSerializer

class UsuarioViewSet(viewsets.ModelViewSet):
    serializer_class = UsuarioSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Usuario.objects.filter(
            tenant=self.request.user.tenant,
            activo=True
        )

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.tenant)