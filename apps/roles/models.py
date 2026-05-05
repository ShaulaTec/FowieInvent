# apps/roles/models.py
import uuid
from django.db import models
from apps.tenants.models import Tenant

class Permiso(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    codigo = models.CharField(max_length=100, unique=True)
    modulo = models.CharField(max_length=50)
    descripcion = models.CharField(max_length=200)

    class Meta:
        db_table = 'permiso'

    def __str__(self):
        return self.codigo


class Rol(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='roles')
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)
    permisos = models.ManyToManyField(Permiso, through='RolPermiso', related_name='roles')

    class Meta:
        db_table = 'rol'
        unique_together = ('tenant', 'nombre')

    def __str__(self):
        return f'{self.tenant} — {self.nombre}'


class RolPermiso(models.Model):
    rol = models.ForeignKey(Rol, on_delete=models.CASCADE)
    permiso = models.ForeignKey(Permiso, on_delete=models.CASCADE)

    class Meta:
        db_table = 'rol_permiso'
        unique_together = ('rol', 'permiso')