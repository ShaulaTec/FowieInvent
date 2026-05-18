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
VER_RBAC           = 'ver_rbac'

# ── Modulo: mi negocio ───────────────────────────────────────────────────────
VER_MI_NEGOCIO    = 'ver_mi_negocio'
EDITAR_MI_NEGOCIO = 'editar_mi_negocio'


MODULOS_SISTEMA = [
    # (codigo, nombre, label, icono, ruta, descripcion, precio_mensual)
    ('inventory', 'Inventario',       'Inventario',       'pi pi-box',      '/system/inventory',   'Control de productos, movimientos y stock.', 0),
    ('rbac',      'Usuarios y Roles', 'Usuarios y Roles', 'pi pi-shield',   '/system/rbac',        'Gestion de usuarios y permisos.',            0),
    ('tenants',   'Mi Negocio',       'Mi Negocio',       'pi pi-building', '/system/my-business', 'Configuracion del negocio.',                 0),
]

PERMISOS_SISTEMA = [
    # (codigo, modulo_codigo, submodulo, ruta, icono, descripcion)

    # ── Inventario ──────────────────────────────────────────────────────────
    (VER_INVENTARIO,       'inventory', 'Inventario',  '/system/inventory/dashboard',  'pi pi-home',     'Ver productos, categorias y stock del inventario.'),
    (EDITAR_PRODUCTO,      'inventory', 'Productos',   '/system/inventory/products',   'pi pi-box',      'Crear y modificar productos del inventario.'),
    (ELIMINAR_PRODUCTO,    'inventory', 'Productos',   '/system/inventory/products',   'pi pi-box',      'Eliminar (logicamente) productos del inventario.'),
    (REGISTRAR_MOVIMIENTO, 'inventory', 'Productos',   '/system/inventory/products',   'pi pi-box',      'Registrar entradas y salidas de stock.'),
    (VER_HISTORIAL,        'inventory', 'Productos',   '/system/inventory/products',   'pi pi-box',      'Consultar el historial de movimientos.'),
    (GESTIONAR_CATEGORIAS, 'inventory', 'Categorías',  '/system/inventory/categories', 'pi pi-tag',      'Crear, editar y eliminar categorias.'),

    # ── RBAC ────────────────────────────────────────────────────────────────
    (VER_RBAC,           'rbac', 'Usuarios y Roles', '/system/rbac/dashboard',       'pi pi-home', 'Acceder al modulo de usuarios y roles.'),
    (GESTIONAR_USUARIOS, 'rbac', 'Usuarios',         '/system/rbac/users', 'pi pi-users',  'Crear, editar y desactivar usuarios del tenant.'),
    (GESTIONAR_ROLES,    'rbac', 'Roles',            '/system/rbac/roles', 'pi pi-shield', 'Crear roles y asignar permisos a los roles.'),

    # ── Mi negocio ──────────────────────────────────────────────────────────
    (VER_MI_NEGOCIO,    'tenants', 'Mi Negocio', '/system/my-business', 'pi pi-building', 'Ver la informacion del negocio.'),
    (EDITAR_MI_NEGOCIO, 'tenants', 'Mi Negocio', '/system/my-business', 'pi pi-building', 'Editar la informacion del negocio.'),
]
