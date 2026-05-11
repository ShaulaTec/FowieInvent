# apps/inventory/models.py
import uuid
from django.db import models, transaction
from apps.tenants.models import Tenant
from apps.users.models import Usuario
from django.core.exceptions import ValidationError


def _ruta_imagen_producto(instance, filename):
    """
    Namespacea las imagenes por tenant para mantener limpio el bucket:
        productos/<tenant_id>/<uuid>_<filename>
    """
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'bin'
    nombre = f'{uuid.uuid4().hex}.{ext}'
    tenant_id = getattr(instance, 'tenant_id', None) or 'sin_tenant'
    return f'productos/{tenant_id}/{nombre}'

class Categoria(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='categorias')
    nombre = models.CharField(max_length=100)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'categoria'
        unique_together = ('tenant', 'nombre')

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='productos')
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name='productos')
    nombre = models.CharField(max_length=200)
    unidad_medida = models.CharField(max_length=50)
    stock_actual = models.IntegerField(default=0)
    stock_minimo = models.IntegerField(default=0)
    imagen = models.ImageField(
        upload_to=_ruta_imagen_producto,
        null=True,
        blank=True,
        help_text='Imagen del producto (opcional).',
    )
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'producto'

    def __str__(self):
        return self.nombre


class Movimiento(models.Model):
    class Tipo(models.TextChoices):
        ENTRADA = 'entrada', 'Entrada'
        SALIDA = 'salida', 'Salida'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name='movimientos')
    usuario = models.ForeignKey(Usuario, on_delete=models.PROTECT, related_name='movimientos')
    tipo = models.CharField(max_length=10, choices=Tipo.choices)
    cantidad = models.IntegerField()
    motivo = models.CharField(max_length=200, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'movimiento'

    def save(self, *args, **kwargs):
        with transaction.atomic():
            producto = self.producto
            if self.tipo == self.Tipo.ENTRADA:
                producto.stock_actual += self.cantidad
            elif self.tipo == self.Tipo.SALIDA:
                if producto.stock_actual < self.cantidad:
                    raise ValidationError("No hay suficiente stock para realizar esta salida.")
                producto.stock_actual -= self.cantidad
            producto.save()
            super().save(*args, **kwargs)