# apps/roles/permisos.py
"""
Catalogo canonico de codigos de permisos del sistema.

Los permisos son definidos por el sistema (no por los tenants) — cualquier
codigo nuevo debe agregarse aqui Y en la migracion de datos correspondiente
en apps/roles/migrations/. Los tenants asignan estos permisos a los roles
que crean, pero no pueden inventar codigos nuevos.

Convencion: snake_case, prefijo por accion (ver_, editar_, eliminar_,
registrar_, generar_, gestionar_).
"""

# ── Modulo: inventory ────────────────────────────────────────────────────────
VER_INVENTARIO       = 'ver_inventario'
EDITAR_PRODUCTO      = 'editar_producto'
ELIMINAR_PRODUCTO    = 'eliminar_producto'
REGISTRAR_MOVIMIENTO = 'registrar_movimiento'
VER_HISTORIAL        = 'ver_historial'
GENERAR_REPORTE      = 'generar_reporte'
GESTIONAR_CATEGORIAS = 'gestionar_categorias'

# ── Modulo: administracion del tenant ────────────────────────────────────────
GESTIONAR_USUARIOS = 'gestionar_usuarios'
GESTIONAR_ROLES    = 'gestionar_roles'


# Estructura usada por la migracion de seed y por el endpoint que lista
# permisos disponibles por modulo.
PERMISOS_SISTEMA = [
    # (codigo, modulo, descripcion)
    (VER_INVENTARIO,       'inventory', 'Ver productos, categorias y stock del inventario.'),
    (EDITAR_PRODUCTO,      'inventory', 'Crear y modificar productos del inventario.'),
    (ELIMINAR_PRODUCTO,    'inventory', 'Eliminar (logicamente) productos del inventario.'),
    (REGISTRAR_MOVIMIENTO, 'inventory', 'Registrar entradas y salidas de stock.'),
    (VER_HISTORIAL,        'inventory', 'Consultar el historial de movimientos.'),
    (GENERAR_REPORTE,      'inventory', 'Generar y exportar reportes de inventario.'),
    (GESTIONAR_CATEGORIAS, 'inventory', 'Crear, editar y eliminar categorias.'),
    (GESTIONAR_USUARIOS,   'tenants',   'Crear, editar y desactivar usuarios del tenant.'),
    (GESTIONAR_ROLES,      'tenants',   'Crear roles y asignar permisos a los roles.'),
]
