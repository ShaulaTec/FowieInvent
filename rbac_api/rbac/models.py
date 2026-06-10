from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class Permission(models.Model):
    name = models.CharField(max_length=100, unique=True)
    codename = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "rbac_permissions"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.codename})"


class Role(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    permissions = models.ManyToManyField(
        Permission,
        through="RolePermission",
        related_name="roles",
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "rbac_roles"
        ordering = ["name"]

    def __str__(self):
        return self.name


class RolePermission(models.Model):
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="role_permissions")
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE, related_name="role_permissions")
    granted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "rbac_role_permissions"
        unique_together = ("role", "permission")

    def __str__(self):
        return f"{self.role.name} → {self.permission.codename}"


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("El email es obligatorio.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    roles = models.ManyToManyField(
        Role,
        through="UserRole",
        related_name="users",
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        db_table = "rbac_users"
        ordering = ["email"]

    def __str__(self):
        return self.email

    def has_permission(self, codename: str) -> bool:
        """Verifica si el usuario tiene un permiso específico a través de sus roles."""
        return (
            RolePermission.objects.filter(
                role__userrole__user=self,
                permission__codename=codename,
            ).exists()
        )

    def get_all_permissions_codenames(self):
        """Retorna todos los codenames de permisos del usuario."""
        return list(
            Permission.objects.filter(
                role_permissions__role__userrole__user=self
            ).values_list("codename", flat=True).distinct()
        )


class UserRole(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_roles")
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="user_roles")
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "rbac_user_roles"
        unique_together = ("user", "role")

    def __str__(self):
        return f"{self.user.email} → {self.role.name}"
