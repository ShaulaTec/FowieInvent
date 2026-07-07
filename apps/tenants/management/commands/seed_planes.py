from django.core.management.base import BaseCommand
from apps.tenants.models import Plan
from apps.payments.models import Plan as BillingPlan
from apps.payments.services import PlanService

PLANES = [
    {
        'nombre': 'Básico', 'max_usuarios': 1, 'max_productos': 100,
        'max_categorias': 10, 'precio_mensual': 199, 'billing': None,
    },
    {
        'nombre': 'Estándar', 'max_usuarios': 3, 'max_productos': 500,
        'max_categorias': 50, 'precio_mensual': 399,
        'billing': {'amount': 39900, 'currency': 'mxn', 'interval': 'month', 'interval_count': 1},
    },
    {
        'nombre': 'Pro', 'max_usuarios': 5, 'max_productos': 999,
        'max_categorias': 999, 'precio_mensual': 699,
        'billing': {'amount': 69900, 'currency': 'mxn', 'interval': 'month', 'interval_count': 1},
    },
]


class Command(BaseCommand):
    help = 'Carga los planes del sistema y sus planes de facturación en Stripe.'

    def handle(self, *args, **kwargs):
        creados = 0
        sincronizados = 0

        for data in PLANES:
            billing_data = data.pop('billing')

            plan, created = Plan.objects.get_or_create(
                nombre=data['nombre'],
                defaults={**data, 'activo': True}
            )
            if created:
                creados += 1
                self.stdout.write(f'   {data["nombre"]} creado')
            else:
                self.stdout.write(f'   {data["nombre"]} ya existía')

            if billing_data and not plan.billing_plan:
                billing_plan = BillingPlan.objects.create(
                    name=data['nombre'],
                    amount=billing_data['amount'],
                    currency=billing_data['currency'],
                    interval=billing_data['interval'],
                    interval_count=billing_data['interval_count'],
                    is_active=True,
                )
                try:
                    PlanService.sync_to_stripe(billing_plan)
                except Exception as exc:
                    self.stdout.write(self.style.WARNING(
                        f'   ⚠ No se pudo sincronizar "{data["nombre"]}" con Stripe: {exc}'
                    ))
                else:
                    plan.billing_plan = billing_plan
                    plan.save(update_fields=['billing_plan'])
                    sincronizados += 1
                    self.stdout.write(f'   {data["nombre"]} enlazado a Stripe')

        self.stdout.write(
            self.style.SUCCESS(
                f'\n{creados} planes creados, {sincronizados} sincronizados con Stripe.'
            )
        )