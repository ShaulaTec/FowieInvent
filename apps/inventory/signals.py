# apps/inventario/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Producto
from apps.notifications.models import Notificacion

@receiver(post_save, sender=Producto)
def evaluar_stock_producto(sender, instance, created, **kwargs):
    """
    Se ejecuta automáticamente CADA vez que un producto se crea o se actualiza.
    """
    # Si el producto no está activo, no nos interesan sus alertas
    if not instance.activo:
        return

    # Evaluamos la condición de stock bajo
    if instance.stock_actual <= instance.stock_minimo:
        mensaje_alerta = (
            f"El producto '{instance.nombre}' tiene un stock actual de {instance.stock_actual}, "
            f"que es menor o igual al stock mínimo de {instance.stock_minimo}."
        )

        # Evitamos duplicados buscando alertas activas (no leídas) de este tipo para este tenant
        notificacion_existe = Notificacion.objects.filter(
            tenant=instance.tenant,
            tipo='stock_bajo',
            modulo='inventario',
            mensaje=mensaje_alerta,
            leida=False
        ).exists()

        if not notificacion_existe:
            Notificacion.objects.create(
                tenant=instance.tenant,
                tipo='stock_bajo',
                modulo='inventario',
                mensaje=mensaje_alerta,
                leida=False
            )