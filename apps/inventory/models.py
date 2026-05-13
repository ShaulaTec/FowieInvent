# apps/inventory/models.py
import uuid
from django.db import models, transaction
from apps.tenants.models import Tenant
from apps.users.models import Usuario
from apps.tenants.models import Tenant, Plan
from django.core.exceptions import ValidationError
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

    def save(self, *args, **kwargs):
        plan = self.tenant.plan # Obtener el plan del tenant
        categorias_count = self.tenant.categorias.count() # Contar las categorías existentes para el tenant
        max_categorias = plan.max_categorias # Obtener el límite de categorías del plan

        if categorias_count >= max_categorias:
            # AQUI ES DONDE SE MUESTRA EL ERROR EN NAVEGADOR, HAY QUE MOSTRARLO EN EL FRONTEND
            raise ValidationError("El plan actual no permite agregar más categorías.")
        super().save(*args, **kwargs) # Guardar la categoría si no se ha alcanzado el límite

class Producto(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='productos')
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name='productos')   
    nombre = models.CharField(max_length=200)
    unidad_medida = models.CharField(max_length=50)
    stock_actual = models.IntegerField(default=0)
    stock_minimo = models.IntegerField(default=0)
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'producto'

    def __str__(self):
        return self.nombre
    
    def save(self, *args, **kwargs):
        
        plan = self.tenant.plan # Obtener el plan del tenant
        productos_count = self.tenant.productos.count() # Contar los productos existentes para el tenant
        max_productos = plan.max_productos # Obtener el límite de productos del plan

        if productos_count >= max_productos:
            # AQUI ES DONDE SE MUESTRA EL ERROR EN NAVEGADOR, HAY QUE MOSTRARLO EN EL FRONTEND
            raise ValidationError("El plan actual no permite agregar más productos.")
        
        super().save(*args, **kwargs) # Guardar el producto si no se ha alcanzado el límite



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
                    raise ValueError("No hay suficiente stock para realizar esta salida.")
                producto.stock_actual -= self.cantidad
            producto.save()
            super().save(*args, **kwargs)