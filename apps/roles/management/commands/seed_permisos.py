# apps/roles/management/commands/seed_permisos.py
from django.core.management.base import BaseCommand
from apps.roles.models import Permiso
from apps.roles.permisos import PERMISOS_SISTEMA

class Command(BaseCommand):
    help = 'Carga el catálogo de permisos del sistema.'

    def handle(self, *args, **kwargs):
        creados = 0
        actualizados = 0
        for codigo, modulo, submodulo, ruta, icono, descripcion in PERMISOS_SISTEMA:
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
                self.stdout.write(f'  ✓ creado: {codigo}')
            else:
                # Actualiza campos si ya existía sin ellos
                updated = False
                for campo, valor in [('submodulo', submodulo), ('ruta', ruta), ('icono', icono)]:
                    if not getattr(obj, campo):
                        setattr(obj, campo, valor)
                        updated = True
                if updated:
                    obj.save()
                    actualizados += 1
                    self.stdout.write(f'  ↻ actualizado: {codigo}')

        self.stdout.write(
            self.style.SUCCESS(
                f'\n{creados} creados, {actualizados} actualizados, {len(PERMISOS_SISTEMA) - creados - actualizados} sin cambios.'
            )
        )