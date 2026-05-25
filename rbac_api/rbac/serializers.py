from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import Permission, Role, RolePermission, User, UserRole


# ─────────────────────────────────────────────
# Permission
# ─────────────────────────────────────────────

class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ["id", "name", "codename", "description", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


# ─────────────────────────────────────────────
# Role
# ─────────────────────────────────────────────

class RolePermissionInlineSerializer(serializers.ModelSerializer):
    permission = PermissionSerializer(read_only=True)

    class Meta:
        model = RolePermission
        fields = ["id", "permission", "granted_at"]


class RoleSerializer(serializers.ModelSerializer):
    permissions = PermissionSerializer(many=True, read_only=True)

    class Meta:
        model = Role
        fields = ["id", "name", "description", "permissions", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class RoleWriteSerializer(serializers.ModelSerializer):
    """Usado en POST/PUT/PATCH — acepta IDs de permisos."""
    permission_ids = serializers.PrimaryKeyRelatedField(
        queryset=Permission.objects.all(),
        many=True,
        write_only=True,
        required=False,
        source="permissions",
    )

    class Meta:
        model = Role
        fields = ["id", "name", "description", "permission_ids"]
        read_only_fields = ["id"]

    def create(self, validated_data):
        permissions = validated_data.pop("permissions", [])
        role = Role.objects.create(**validated_data)
        for perm in permissions:
            RolePermission.objects.create(role=role, permission=perm)
        return role

    def update(self, instance, validated_data):
        permissions = validated_data.pop("permissions", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if permissions is not None:
            instance.role_permissions.all().delete()
            for perm in permissions:
                RolePermission.objects.create(role=instance, permission=perm)
        return instance


# ─────────────────────────────────────────────
# RolePermission (tabla intermedia)
# ─────────────────────────────────────────────

class RolePermissionSerializer(serializers.ModelSerializer):
    role_id = serializers.PrimaryKeyRelatedField(queryset=Role.objects.all(), source="role")
    permission_id = serializers.PrimaryKeyRelatedField(queryset=Permission.objects.all(), source="permission")
    role = RoleSerializer(read_only=True)
    permission = PermissionSerializer(read_only=True)

    class Meta:
        model = RolePermission
        fields = ["id", "role_id", "role", "permission_id", "permission", "granted_at"]
        read_only_fields = ["id", "role", "permission", "granted_at"]

    def validate(self, attrs):
        if RolePermission.objects.filter(role=attrs["role"], permission=attrs["permission"]).exists():
            raise serializers.ValidationError("Este permiso ya está asignado a ese rol.")
        return attrs


# ─────────────────────────────────────────────
# User
# ─────────────────────────────────────────────

class UserRoleInlineSerializer(serializers.ModelSerializer):
    role = RoleSerializer(read_only=True)

    class Meta:
        model = UserRole
        fields = ["id", "role", "assigned_at"]


class UserSerializer(serializers.ModelSerializer):
    roles = RoleSerializer(many=True, read_only=True)
    all_permissions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "email", "first_name", "last_name",
            "is_active", "is_staff", "roles",
            "all_permissions", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "all_permissions"]

    def get_all_permissions(self, obj):
        return obj.get_all_permissions_codenames()


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    role_ids = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.all(),
        many=True,
        write_only=True,
        required=False,
        source="roles",
    )

    class Meta:
        model = User
        fields = [
            "id", "email", "first_name", "last_name",
            "password", "password_confirm", "role_ids",
        ]
        read_only_fields = ["id"]

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password_confirm"):
            raise serializers.ValidationError({"password_confirm": "Las contraseñas no coinciden."})
        return attrs

    def create(self, validated_data):
        roles = validated_data.pop("roles", [])
        password = validated_data.pop("password")
        user = User.objects.create_user(password=password, **validated_data)
        for role in roles:
            UserRole.objects.create(user=user, role=role)
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    role_ids = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.all(),
        many=True,
        write_only=True,
        required=False,
        source="roles",
    )

    class Meta:
        model = User
        fields = ["email", "first_name", "last_name", "is_active", "is_staff", "role_ids"]

    def update(self, instance, validated_data):
        roles = validated_data.pop("roles", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if roles is not None:
            instance.user_roles.all().delete()
            for role in roles:
                UserRole.objects.create(user=instance, role=role)
        return instance


# ─────────────────────────────────────────────
# UserRole (tabla intermedia)
# ─────────────────────────────────────────────

class UserRoleSerializer(serializers.ModelSerializer):
    user_id = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), source="user")
    role_id = serializers.PrimaryKeyRelatedField(queryset=Role.objects.all(), source="role")
    user = UserSerializer(read_only=True)
    role = RoleSerializer(read_only=True)

    class Meta:
        model = UserRole
        fields = ["id", "user_id", "user", "role_id", "role", "assigned_at"]
        read_only_fields = ["id", "user", "role", "assigned_at"]

    def validate(self, attrs):
        if UserRole.objects.filter(user=attrs["user"], role=attrs["role"]).exists():
            raise serializers.ValidationError("Este rol ya está asignado al usuario.")
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError({"new_password_confirm": "Las contraseñas no coinciden."})
        return attrs
