from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import PermisoViewSet, RolViewSet, RolPermisoViewSet, rbac_stats

router = DefaultRouter()
router.register('permisos',     PermisoViewSet,    basename='permiso')
router.register('roles',        RolViewSet,        basename='rol')
router.register('rol-permisos', RolPermisoViewSet, basename='rol-permiso')

urlpatterns = [
    path('', include(router.urls)),
    path('stats/', rbac_stats, name='rbac-stats'),
]