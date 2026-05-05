# apps/tenants/models.py
import uuid
from django.db import models

class Plan(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=100)
    max_usuarios = models.IntegerField()
    max_productos = models.IntegerField()
    max_categorias = models.IntegerField()
    precio_mensual = models.DecimalField(max_digits=10, decimal_places=2)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'plan'

    def __str__(self):
        return self.nombre


class Modulo(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    codigo = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    precio_mensual = models.DecimalField(max_digits=10, decimal_places=2)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'modulo'

    def __str__(self):
        return self.nombre


class Tenant(models.Model):
    class Estado(models.TextChoices):
        ACTIVO = 'activo', 'Activo'
        INACTIVO = 'inactivo', 'Inactivo'
        SUSPENDIDO = 'suspendido', 'Suspendido'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name='tenants')
    nombre_negocio = models.CharField(max_length=200)
    email_contacto = models.EmailField(unique=True)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.ACTIVO)
    fecha_registro = models.DateField(auto_now_add=True)
    fecha_vencimiento = models.DateField()

    class Meta:
        db_table = 'tenant'

    def __str__(self):
        return self.nombre_negocio


class TenantModulo(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='modulos')
    modulo = models.ForeignKey(Modulo, on_delete=models.PROTECT, related_name='tenants')
    fecha_activacion = models.DateField(auto_now_add=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'tenant_modulo'
        unique_together = ('tenant', 'modulo')