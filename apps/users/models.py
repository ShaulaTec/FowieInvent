import uuid
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from apps.tenants.models import Tenant, Plan
from apps.roles.models import Rol


class UsuarioManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('El email es obligatorio')
        user = self.model(
            email=self.normalize_email(email),
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('activo', True)
        return self.create_user(email, password, **extra_fields)


class Usuario(AbstractBaseUser, PermissionsMixin):
    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant        = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='usuarios', null=True, blank=True)
    rol           = models.ForeignKey(Rol, on_delete=models.PROTECT, related_name='usuarios', null=True, blank=True)
    email         = models.EmailField(unique=True)
    activo        = models.BooleanField(default=True)
    ultimo_acceso = models.DateTimeField(null=True, blank=True)

    # Campos requeridos por Django
    is_staff      = models.BooleanField(default=False)
    is_active     = models.BooleanField(default=True)

    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = []

    objects = UsuarioManager()

    class Meta:
        db_table = 'usuario'

    def __str__(self):
        return self.email
