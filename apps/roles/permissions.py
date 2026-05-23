# apps/roles/permissions.py
"""
Sistema reutilizable de autorizacion basado en permisos (RBAC dinamico).

Expone tres herramientas que cubren todos los estilos de vistas del proyecto:

1. `TienePermiso`         — clase BasePermission de DRF.
2. `requiere_permiso(...)` — decorador para acciones individuales.
3. `PermisoRequeridoMixin` — mixin para ViewSets con mapeo accion -> permiso.

Todas comparten la misma logica de validacion en `usuario_tiene_permiso`
para garantizar un unico camino auditable.

Reglas de seguridad aplicadas (defensa en profundidad):
  - El usuario debe estar autenticado (NFR05).
  - El rol debe pertenecer al mismo tenant que el usuario (NFR01).
  - El rol debe estar activo.
  - El rol 'Owner' (creado en el alta de un tenant) siempre pasa el chequeo;
    el resto debe tener explicitamente el codigo de permiso asignado.
"""
from functools import wraps
from typing import Iterable, Optional, Sequence, Union

from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied

CodigoPermiso = Union[str, Sequence[str]]


# ── Helper central ───────────────────────────────────────────────────────────

def usuario_tiene_permiso(usuario, codigo: CodigoPermiso) -> bool:
    """
    Devuelve True si `usuario` posee al menos uno de los codigos indicados
    dentro de su tenant. Acepta un str o una secuencia de str.
    """
    if usuario is None or not getattr(usuario, 'is_authenticated', False):
        return False

    rol = getattr(usuario, 'rol', None)
    if rol is None or not getattr(rol, 'activo', True):
        return False

    # Aislamiento estricto entre tenants: el rol DEBE pertenecer al tenant
    # del usuario, sin importar lo que diga el token. (NFR01)
    tenant_usuario = getattr(usuario, 'tenant_id', None)
    tenant_rol = getattr(rol, 'tenant_id', None)
    if not tenant_usuario or not tenant_rol or tenant_usuario != tenant_rol:
        return False

    # Bypass para el rol 'Owner' del tenant — el propietario tiene acceso
    # total a su propio negocio por diseno (lo crea RegisterSerializer).
    if getattr(rol, 'nombre', None) == 'Owner':
        return True

    codigos: Iterable[str]
    if isinstance(codigo, str):
        codigos = (codigo,)
    else:
        codigos = tuple(codigo)

    if not codigos:
        return False

    return rol.permisos.filter(codigo__in=codigos).exists()


# ── BasePermission de DRF ────────────────────────────────────────────────────

class TienePermiso(permissions.BasePermission):
    """
    Valida que el usuario autenticado posea el permiso declarado por la vista.

    La vista puede declarar el permiso de tres formas (orden de precedencia):

      1. `permiso_requerido_map = {'create': 'editar_producto', ...}` — mapeo
         por accion de DRF (`view.action`).
      2. `permiso_requerido_default = 'codigo'` — fallback usado cuando la
         accion no aparece en el mapa.
      3. `permiso_requerido = 'codigo'` — atajo cuando toda la vista usa el
         mismo permiso (vistas no-ViewSet, APIView clasica).

    Si la vista no declara ningun permiso, esta clase no bloquea — el resto
    de `permission_classes` (p.ej. IsAuthenticated) decide.
    """
    message = 'No tienes el permiso necesario para realizar esta accion.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        codigo = self._resolver_codigo(view)
        if codigo is None:
            # La vista no declara permiso explicito -> no bloqueamos aqui.
            return True

        return usuario_tiene_permiso(request.user, codigo)

    @staticmethod
    def _resolver_codigo(view) -> Optional[CodigoPermiso]:
        accion = getattr(view, 'action', None)
        mapa = getattr(view, 'permiso_requerido_map', None) or {}
        if accion and accion in mapa:
            return mapa[accion]
        default = getattr(view, 'permiso_requerido_default', None)
        if default is not None:
            return default
        return getattr(view, 'permiso_requerido', None)


# ── Decorador para acciones puntuales ────────────────────────────────────────

def requiere_permiso(*codigos: str):
    """
    Decorador para metodos de vistas (incluidas @action) que levanta
    PermissionDenied (HTTP 403) si el usuario no posee ninguno de los
    `codigos` indicados.

    Util cuando una accion necesita un permiso distinto al declarado a nivel
    de viewset, o para proteger funciones sueltas.

        from apps.roles.permissions import requiere_permiso
        from apps.roles.permisos import REGISTRAR_MOVIMIENTO

        class MovimientoViewSet(ModelViewSet):
            @action(detail=False, methods=['post'])
            @requiere_permiso(REGISTRAR_MOVIMIENTO)
            def registrar(self, request): ...
    """
    if not codigos:
        raise ValueError('requiere_permiso necesita al menos un codigo.')

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(self, request, *args, **kwargs):
            if not usuario_tiene_permiso(request.user, codigos):
                raise PermissionDenied(
                    'No tienes el permiso necesario para realizar esta accion.'
                )
            return view_func(self, request, *args, **kwargs)
        return wrapper

    return decorator


# ── Mixin reutilizable para ViewSets ─────────────────────────────────────────

class PermisoRequeridoMixin:
    """
    Mixin para `GenericViewSet` / `ModelViewSet` que aplica `TienePermiso`
    automaticamente y resuelve el codigo de permiso usando
    `permiso_requerido_map` (dict accion -> codigo).

        from apps.roles.permissions import PermisoRequeridoMixin
        from apps.roles.permisos import (
            VER_INVENTARIO, EDITAR_PRODUCTO, ELIMINAR_PRODUCTO,
        )

        class ProductoViewSet(PermisoRequeridoMixin, viewsets.ModelViewSet):
            permiso_requerido_map = {
                'list':           VER_INVENTARIO,
                'retrieve':       VER_INVENTARIO,
                'create':         EDITAR_PRODUCTO,
                'update':         EDITAR_PRODUCTO,
                'partial_update': EDITAR_PRODUCTO,
                'destroy':        ELIMINAR_PRODUCTO,
            }

    Acciones que no aparezcan en el mapa usan `permiso_requerido_default`
    si esta definido; si tampoco, la accion queda solo protegida por
    autenticacion (NO se asume "permitir" para acciones sensibles —
    se recomienda mapear TODAS las acciones expuestas).
    """
    permiso_requerido_map: dict = {}
    permiso_requerido_default: Optional[str] = None

    def get_permissions(self):
        clases = list(super().get_permissions())
        if not any(isinstance(c, TienePermiso) for c in clases):
            clases.append(TienePermiso())
        return clases
