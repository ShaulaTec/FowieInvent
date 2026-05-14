# apps/users/views.py
from rest_framework import viewsets, permissions, generics, status
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from apps.roles.permissions import PermisoRequeridoMixin
from apps.roles.permisos import GESTIONAR_USUARIOS
from .models import Usuario
from .serializers import UsuarioSerializer, RegisterSerializer, EmailTokenObtainPairSerializer
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from apps.roles.permisos import PERMISOS_SISTEMA


class EmailTokenObtainPairView(TokenObtainPairView):
    serializer_class = EmailTokenObtainPairSerializer


class UsuarioViewSet(PermisoRequeridoMixin, viewsets.ModelViewSet):
    serializer_class   = UsuarioSerializer
    permission_classes = [permissions.IsAuthenticated]
    permiso_requerido_map = {
        'list':           GESTIONAR_USUARIOS,
        'retrieve':       GESTIONAR_USUARIOS,
        'create':         GESTIONAR_USUARIOS,
        'update':         GESTIONAR_USUARIOS,
        'partial_update': GESTIONAR_USUARIOS,
        'destroy':        GESTIONAR_USUARIOS,
    }

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

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    user = request.user
    rol = user.rol
    if rol.nombre == 'Owner':
        permisos = [
            {'codigo': p[0], 'modulo': p[1], 'submodulo': p[2], 'ruta': p[3], 'icono': p[4]}
            for p in PERMISOS_SISTEMA
        ]
    else:
        permisos = list(
            rol.permisos.values('codigo', 'modulo', 'submodulo', 'ruta', 'icono')
        )
    return Response({
        'id':       str(user.id),
        'email':    user.email,
        'tenant':   str(user.tenant.id),
        'rol':      rol.nombre,
        'permisos': permisos,
    })