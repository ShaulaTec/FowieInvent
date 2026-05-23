from django.core.management.base import BaseCommand
from apps.tenants.models import Plan

PLANES = [
    {'nombre': 'Básico',    'max_usuarios': 1, 'max_productos': 100, 'max_categorias': 10,  'precio_mensual': 199},
    {'nombre': 'Estándar',  'max_usuarios': 3, 'max_productos': 500, 'max_categorias': 50,  'precio_mensual': 399},
    {'nombre': 'Pro',       'max_usuarios': 5, 'max_productos': 999, 'max_categorias': 999, 'precio_mensual': 699},
]

class Command(BaseCommand):
    help = 'Carga los planes del sistema.'

    def handle(self, *args, **kwargs):
        creados = 0
        for data in PLANES:
            _, created = Plan.objects.get_or_create(
                nombre=data['nombre'],
                defaults={**data, 'activo': True}
            )
            if created:
                creados += 1
                self.stdout.write(f'   {data["nombre"]}')

        self.stdout.write(
            self.style.SUCCESS(f'\n{creados} planes creados.')
        )
