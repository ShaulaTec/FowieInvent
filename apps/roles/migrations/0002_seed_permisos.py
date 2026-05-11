# apps/roles/migrations/0002_seed_permisos.py
"""
Siembra el catalogo de permisos del sistema en la tabla `permiso`.

Los permisos los define el sistema (FR08): los tenants no pueden crear
codigos nuevos. Esta migracion es idempotente — usa update_or_create
para que ejecutarla varias veces no genere duplicados ni borre datos
existentes.
"""
from django.db import migrations


def seed_permisos(apps, schema_editor):
    Permiso = apps.get_model('roles', 'Permiso')

    # Mantener sincronizado con apps/roles/permisos.py
    permisos = [
        ('ver_inventario',       'inventory', 'Ver productos, categorias y stock del inventario.'),
        ('editar_producto',      'inventory', 'Crear y modificar productos del inventario.'),
        ('eliminar_producto',    'inventory', 'Eliminar (logicamente) productos del inventario.'),
        ('registrar_movimiento', 'inventory', 'Registrar entradas y salidas de stock.'),
        ('ver_historial',        'inventory', 'Consultar el historial de movimientos.'),
        ('generar_reporte',      'inventory', 'Generar y exportar reportes de inventario.'),
        ('gestionar_categorias', 'inventory', 'Crear, editar y eliminar categorias.'),
        ('gestionar_usuarios',   'tenants',   'Crear, editar y desactivar usuarios del tenant.'),
        ('gestionar_roles',      'tenants',   'Crear roles y asignar permisos a los roles.'),
    ]

    for codigo, modulo, descripcion in permisos:
        Permiso.objects.update_or_create(
            codigo=codigo,
            defaults={'modulo': modulo, 'descripcion': descripcion},
        )


def unseed_permisos(apps, schema_editor):
    Permiso = apps.get_model('roles', 'Permiso')
    codigos = [
        'ver_inventario', 'editar_producto', 'eliminar_producto',
        'registrar_movimiento', 'ver_historial', 'generar_reporte',
        'gestionar_categorias', 'gestionar_usuarios', 'gestionar_roles',
    ]
    Permiso.objects.filter(codigo__in=codigos).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('roles', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_permisos, unseed_permisos),
    ]
