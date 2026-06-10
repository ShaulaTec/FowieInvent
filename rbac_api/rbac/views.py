from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Permission, Role, RolePermission, User, UserRole
from .permissions import HasPermission, IsSuperUserOrReadOnly
from .serializers import (
    ChangePasswordSerializer,
    PermissionSerializer,
    RolePermissionSerializer,
    RoleSerializer,
    RoleWriteSerializer,
    UserCreateSerializer,
    UserRoleSerializer,
    UserSerializer,
    UserUpdateSerializer,
)


# ─────────────────────────────────────────────
# Permission ViewSet  —  /api/permissions/
# ─────────────────────────────────────────────

class PermissionViewSet(viewsets.ModelViewSet):
    """
    CRUD completo de permisos.

    list        GET    /api/permissions/
    create      POST   /api/permissions/
    retrieve    GET    /api/permissions/{id}/
    update      PUT    /api/permissions/{id}/
    partial     PATCH  /api/permissions/{id}/
    destroy     DELETE /api/permissions/{id}/
    """
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [IsAuthenticated, IsSuperUserOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(name__icontains=search) | qs.filter(codename__icontains=search)
        return qs


# ─────────────────────────────────────────────
# Role ViewSet  —  /api/roles/
# ─────────────────────────────────────────────

class RoleViewSet(viewsets.ModelViewSet):
    """
    CRUD completo de roles.

    list        GET    /api/roles/
    create      POST   /api/roles/
    retrieve    GET    /api/roles/{id}/
    update      PUT    /api/roles/{id}/
    partial     PATCH  /api/roles/{id}/
    destroy     DELETE /api/roles/{id}/

    Acciones extra:
    permissions GET    /api/roles/{id}/permissions/        -> permisos del rol
    add-perm    POST   /api/roles/{id}/add-permission/     -> agregar permiso
    remove-perm DELETE /api/roles/{id}/remove-permission/  -> quitar permiso
    """
    queryset = Role.objects.prefetch_related("permissions").all()
    permission_classes = [IsAuthenticated, IsSuperUserOrReadOnly]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return RoleWriteSerializer
        return RoleSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(name__icontains=search)
        return qs

    @action(detail=True, methods=["get"], url_path="permissions")
    def permissions(self, request, pk=None):
        role = self.get_object()
        serializer = PermissionSerializer(role.permissions.all(), many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="add-permission")
    def add_permission(self, request, pk=None):
        role = self.get_object()
        perm_id = request.data.get("permission_id")
        permission = get_object_or_404(Permission, pk=perm_id)
        rp, created = RolePermission.objects.get_or_create(role=role, permission=permission)
        if not created:
            return Response(
                {"detail": "El permiso ya está asignado a este rol."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(RolePermissionSerializer(rp).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["delete"], url_path="remove-permission")
    def remove_permission(self, request, pk=None):
        role = self.get_object()
        perm_id = request.data.get("permission_id")
        deleted, _ = RolePermission.objects.filter(role=role, permission_id=perm_id).delete()
        if not deleted:
            return Response(
                {"detail": "El permiso no estaba asignado a este rol."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


# ─────────────────────────────────────────────
# RolePermission ViewSet  —  /api/role-permissions/
# ─────────────────────────────────────────────

class RolePermissionViewSet(viewsets.ModelViewSet):
    """
    Gestión directa de la tabla intermedia Role ↔ Permission.

    list     GET    /api/role-permissions/
    create   POST   /api/role-permissions/
    retrieve GET    /api/role-permissions/{id}/
    destroy  DELETE /api/role-permissions/{id}/
    """
    queryset = RolePermission.objects.select_related("role", "permission").all()
    serializer_class = RolePermissionSerializer
    permission_classes = [IsAuthenticated, IsSuperUserOrReadOnly]
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_queryset(self):
        qs = super().get_queryset()
        role_id = self.request.query_params.get("role_id")
        perm_id = self.request.query_params.get("permission_id")
        if role_id:
            qs = qs.filter(role_id=role_id)
        if perm_id:
            qs = qs.filter(permission_id=perm_id)
        return qs


# ─────────────────────────────────────────────
# User ViewSet  —  /api/users/
# ─────────────────────────────────────────────

class UserViewSet(viewsets.ModelViewSet):
    """
    CRUD completo de usuarios.

    list        GET    /api/users/
    create      POST   /api/users/
    retrieve    GET    /api/users/{id}/
    update      PUT    /api/users/{id}/
    partial     PATCH  /api/users/{id}/
    destroy     DELETE /api/users/{id}/

    Acciones extra:
    me              GET    /api/users/me/                      -> perfil propio
    change-password POST   /api/users/{id}/change-password/    -> cambiar contraseña
    roles           GET    /api/users/{id}/roles/              -> roles del usuario
    add-role        POST   /api/users/{id}/add-role/           -> asignar rol
    remove-role     DELETE /api/users/{id}/remove-role/        -> quitar rol
    permissions     GET    /api/users/{id}/permissions/        -> permisos efectivos
    """
    queryset = User.objects.prefetch_related("roles__permissions").all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        if self.action in ("update", "partial_update"):
            return UserUpdateSerializer
        if self.action == "change_password":
            return ChangePasswordSerializer
        return UserSerializer

    def get_permissions(self):
        if self.action in ("list", "create", "destroy"):
            return [IsAuthenticated(), IsSuperUserOrReadOnly()]
        return [IsAuthenticated()]

    def get_queryset(self):
        qs = super().get_queryset()
        search = self.request.query_params.get("search")
        is_active = self.request.query_params.get("is_active")
        role_id = self.request.query_params.get("role_id")
        if search:
            qs = qs.filter(email__icontains=search) | qs.filter(first_name__icontains=search)
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == "true")
        if role_id:
            qs = qs.filter(roles__id=role_id)
        return qs.distinct()

    # ── /api/users/me/ ──────────────────────
    @action(detail=False, methods=["get"], url_path="me")
    def me(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    # ── /api/users/{id}/change-password/ ────
    @action(detail=True, methods=["post"], url_path="change-password")
    def change_password(self, request, pk=None):
        user = self.get_object()
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if not user.check_password(serializer.validated_data["old_password"]):
            return Response(
                {"old_password": "Contraseña actual incorrecta."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.set_password(serializer.validated_data["new_password"])
        user.save()
        return Response({"detail": "Contraseña actualizada correctamente."})

    # ── /api/users/{id}/roles/ ───────────────
    @action(detail=True, methods=["get"], url_path="roles")
    def roles(self, request, pk=None):
        user = self.get_object()
        from .serializers import RoleSerializer as RS
        serializer = RS(user.roles.all(), many=True)
        return Response(serializer.data)

    # ── /api/users/{id}/add-role/ ────────────
    @action(detail=True, methods=["post"], url_path="add-role")
    def add_role(self, request, pk=None):
        user = self.get_object()
        role_id = request.data.get("role_id")
        role = get_object_or_404(Role, pk=role_id)
        ur, created = UserRole.objects.get_or_create(user=user, role=role)
        if not created:
            return Response(
                {"detail": "El rol ya está asignado al usuario."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(UserRoleSerializer(ur).data, status=status.HTTP_201_CREATED)

    # ── /api/users/{id}/remove-role/ ─────────
    @action(detail=True, methods=["delete"], url_path="remove-role")
    def remove_role(self, request, pk=None):
        user = self.get_object()
        role_id = request.data.get("role_id")
        deleted, _ = UserRole.objects.filter(user=user, role_id=role_id).delete()
        if not deleted:
            return Response(
                {"detail": "El rol no estaba asignado al usuario."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    # ── /api/users/{id}/permissions/ ─────────
    @action(detail=True, methods=["get"], url_path="permissions")
    def permissions(self, request, pk=None):
        user = self.get_object()
        return Response({"permissions": user.get_all_permissions_codenames()})


# ─────────────────────────────────────────────
# UserRole ViewSet  —  /api/user-roles/
# ─────────────────────────────────────────────

class UserRoleViewSet(viewsets.ModelViewSet):
    """
    Gestión directa de la tabla intermedia User ↔ Role.

    list     GET    /api/user-roles/
    create   POST   /api/user-roles/
    retrieve GET    /api/user-roles/{id}/
    destroy  DELETE /api/user-roles/{id}/
    """
    queryset = UserRole.objects.select_related("user", "role").all()
    serializer_class = UserRoleSerializer
    permission_classes = [IsAuthenticated, IsSuperUserOrReadOnly]
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_queryset(self):
        qs = super().get_queryset()
        user_id = self.request.query_params.get("user_id")
        role_id = self.request.query_params.get("role_id")
        if user_id:
            qs = qs.filter(user_id=user_id)
        if role_id:
            qs = qs.filter(role_id=role_id)
        return qs
