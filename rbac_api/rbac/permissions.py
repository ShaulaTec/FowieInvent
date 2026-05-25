from functools import wraps

from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsSuperUserOrReadOnly(BasePermission):
    """
    Permite lectura a cualquier usuario autenticado.
    Permite escritura solo a superusuarios.
    """
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return request.user and request.user.is_superuser


class HasPermission(BasePermission):
    """
    Valida que el usuario tenga un codename específico.

    Uso en ViewSet:
        permission_classes = [IsAuthenticated, HasPermission]
        required_permission = "manage_users"

    O dinámico por acción con get_required_permission():
        def get_required_permission(self):
            mapping = {
                "list": "view_users",
                "create": "add_users",
                "destroy": "delete_users",
            }
            return mapping.get(self.action)
    """
    def has_permission(self, request, view):
        if request.user.is_superuser:
            return True

        # Permite a las vistas definir un permiso por acción
        get_perm = getattr(view, "get_required_permission", None)
        if callable(get_perm):
            codename = get_perm()
        else:
            codename = getattr(view, "required_permission", None)

        if not codename:
            return True  # Sin restricción definida

        return request.user.has_permission(codename)


class IsOwnerOrSuperUser(BasePermission):
    """
    Permite acceso al propio usuario o a superusuarios.
    Útil para endpoints como /users/{id}/ donde solo el dueño puede editar.
    """
    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True
        # Soporta tanto objetos User como objetos con campo .user
        owner = obj if hasattr(obj, "email") else getattr(obj, "user", None)
        return owner == request.user


# ─────────────────────────────────────────────
# Decorador funcional para vistas simples (no ViewSets)
# ─────────────────────────────────────────────

def require_permission(codename: str):
    """
    Decorador para vistas basadas en función (@api_view).

    Uso:
        @api_view(["GET"])
        @require_permission("view_reports")
        def my_view(request):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            if not request.user or not request.user.is_authenticated:
                raise PermissionDenied("Se requiere autenticación.")
            if request.user.is_superuser:
                return func(request, *args, **kwargs)
            if not request.user.has_permission(codename):
                raise PermissionDenied(
                    f"Se requiere el permiso '{codename}' para realizar esta acción."
                )
            return func(request, *args, **kwargs)
        return wrapper
    return decorator
