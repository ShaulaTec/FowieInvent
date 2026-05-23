# apps/roles/management/commands/seed_permisos.py
from django.core.management.base import BaseCommand
from apps.roles.models import Permiso
from apps.tenants.models import Modulo
from apps.roles.permisos import MODULOS_SISTEMA, PERMISOS_SISTEMA


class Command(BaseCommand):
    help = 'Carga el catálogo de módulos y permisos del sistema.'

    def handle(self, *args, **kwargs):
        # ── Módulos ──────────────────────────────────────────────────────────
        self.stdout.write('Sembrando módulos...')
        for codigo, nombre, label, icono, ruta, descripcion, precio in MODULOS_SISTEMA:
            obj, created = Modulo.objects.get_or_create(
                codigo=codigo,
                defaults={
                    'nombre':          nombre,
                    'label':           label,
                    'icono':           icono,
                    'ruta':            ruta,
                    'descripcion':     descripcion,
                    'precio_mensual':  precio,
                }
            )
            if not created:
                for campo, valor in [('nombre', nombre), ('label', label), ('icono', icono), ('ruta', ruta)]:
                    if getattr(obj, campo) != valor:
                        setattr(obj, campo, valor)
                obj.save()
            self.stdout.write(f'  {"creado" if created else "ok"}: {codigo}')

        # ── Permisos ─────────────────────────────────────────────────────────
        self.stdout.write('Sembrando permisos...')
        creados = actualizados = 0
        for codigo, modulo_codigo, submodulo, ruta, icono, descripcion in PERMISOS_SISTEMA:
            modulo = Modulo.objects.get(codigo=modulo_codigo)
            obj, created = Permiso.objects.get_or_create(
                codigo=codigo,
                defaults={
                    'modulo':      modulo,
                    'submodulo':   submodulo,
                    'ruta':        ruta,
                    'icono':       icono,
                    'descripcion': descripcion,
                }
            )
            if created:
                creados += 1
                self.stdout.write(f'  creado: {codigo}')
            else:
                updated = False
                for campo, valor in [('modulo', modulo), ('submodulo', submodulo), ('ruta', ruta), ('icono', icono), ('descripcion', descripcion)]:
                    if getattr(obj, campo) != valor:
                        setattr(obj, campo, valor)
                        updated = True
                if updated:
                    obj.save()
                    actualizados += 1
                    self.stdout.write(f'  actualizado: {codigo}')

        self.stdout.write(self.style.SUCCESS(
            f'\n{creados} creados, {actualizados} actualizados.'
        ))
