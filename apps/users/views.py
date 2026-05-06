# apps/users/views.py
from rest_framework import viewsets, permissions, generics, status
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Usuario
from .serializers import UsuarioSerializer, RegisterSerializer, EmailTokenObtainPairSerializer


class EmailTokenObtainPairView(TokenObtainPairView):
    serializer_class = EmailTokenObtainPairSerializer


class UsuarioViewSet(viewsets.ModelViewSet):
    serializer_class   = UsuarioSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Usuario.objects.filter(
            tenant=self.request.user.tenant,
            activo=True,
        )

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.tenant)


class RegisterView(generics.CreateAPIView):
    serializer_class   = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh = RefreshToken.for_user(user)
        return Response({
            'access':  str(refresh.access_token),
            'refresh': str(refresh),
            'user': {
                'id':     str(user.id),
                'email':  user.email,
                'tenant': str(user.tenant.id),
                'rol':    user.rol.nombre,
            }
        }, status=status.HTTP_201_CREATED)
