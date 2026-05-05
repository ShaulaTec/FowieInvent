# apps/users/models.py
import uuid
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.db import models
from apps.tenants.models import Tenant
from apps.roles.models import Rol

class UsuarioManager(BaseUserManager):
    def create_user(self, email, tenant, rol, password=None):
        if not email:
            raise ValueError('El email es obligatorio')
        user = self.model(email=self.normalize_email(email), tenant=tenant, rol=rol)
        user.set_password(password)
        user.save(using=self._db)
        return user


class Usuario(AbstractBaseUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='usuarios')
    rol = models.ForeignKey(Rol, on_delete=models.PROTECT, related_name='usuarios')
    email = models.EmailField(unique=True)
    activo = models.BooleanField(default=True)
    ultimo_acceso = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UsuarioManager()

    class Meta:
        db_table = 'usuario'

    def __str__(self):
        return self.email