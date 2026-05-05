# apps/notifications/views.py
from rest_framework import viewsets, permissions
from .models import Notificacion
from .serializers import NotificacionSerializer

class NotificacionViewSet(viewsets.ModelViewSet):
    serializer_class = NotificacionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notificacion.objects.filter(
            tenant=self.request.user.tenant
        ).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.tenant)