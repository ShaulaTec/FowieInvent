# apps/tenants/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PlanViewSet, ModuloViewSet, TenantViewSet, TenantModuloViewSet

router = DefaultRouter()
router.register('planes', PlanViewSet, basename='plan')
router.register('modulos', ModuloViewSet, basename='modulo')
router.register('info', TenantViewSet, basename='tenant')
router.register('modulos-activos', TenantModuloViewSet, basename='tenant-modulo')

urlpatterns = [path('', include(router.urls))]