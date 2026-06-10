from rest_framework.routers import DefaultRouter

from .views import (
    PermissionViewSet,
    RolePermissionViewSet,
    RoleViewSet,
    UserRoleViewSet,
    UserViewSet,
)

router = DefaultRouter()
router.register(r"permissions", PermissionViewSet, basename="permission")
router.register(r"roles", RoleViewSet, basename="role")
router.register(r"role-permissions", RolePermissionViewSet, basename="role-permission")
router.register(r"users", UserViewSet, basename="user")
router.register(r"user-roles", UserRoleViewSet, basename="user-role")

urlpatterns = router.urls
