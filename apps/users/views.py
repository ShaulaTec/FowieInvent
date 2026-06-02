from rest_framework import viewsets, permissions, generics, status
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from apps.roles.permissions import PermisoRequeridoMixin
from apps.roles.permisos import GESTIONAR_USUARIOS
from apps.roles.models import Permiso
from .models import Usuario
from .serializers import UsuarioSerializer, RegisterSerializer, EmailTokenObtainPairSerializer


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

    def update(self, request, *args, **kwargs):
        usuario_target = self.get_object()
        rol_id_nuevo   = request.data.get('rol_id')

        if (usuario_target == request.user
                and request.user.rol.nombre == 'Owner'
                and rol_id_nuevo is not None
                and str(request.user.rol.id) != str(rol_id_nuevo)):
            raise PermissionDenied(
                'Un Owner no puede cambiar su propio rol. '
                'Pide a otro Owner que lo haga.'
            )

        if (usuario_target != request.user
                and usuario_target.rol.nombre == 'Owner'
                and rol_id_nuevo is not None
                and str(usuario_target.rol.id) != str(rol_id_nuevo)
                and request.user.rol.nombre != 'Owner'):
            raise PermissionDenied(
                'Solo un Owner puede cambiar el rol de otro Owner.'
            )

        return super().update(request, *args, **kwargs)

class RegisterView(generics.CreateAPIView):
    serializer_class   = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user    = serializer.save()
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
    rol  = user.rol

    modulos_activos = user.tenant.modulos.filter(
        activo=True
    ).values_list('modulo__codigo', flat=True)

    if rol.nombre == 'Owner':
        permisos_qs = Permiso.objects.filter(
            modulo__codigo__in=modulos_activos
        ).select_related('modulo')
    else:
        permisos_qs = rol.permisos.filter(
            modulo__codigo__in=modulos_activos
        ).select_related('modulo')

    permisos = [
        {
            'codigo':    p.codigo,
            'submodulo': p.submodulo,
            'ruta':      p.ruta,
            'icono':     p.icono,
            'modulo': {
                'codigo': p.modulo.codigo,
                'label':  p.modulo.label,
                'icono':  p.modulo.icono,
                'ruta':   p.modulo.ruta,
            } if p.modulo else None,
        }
        for p in permisos_qs
    ]

    return Response({
        'id':       str(user.id),
        'email':    user.email,
        'tenant':   str(user.tenant.id),
        'rol':      rol.nombre,
        'permisos': permisos,
    })