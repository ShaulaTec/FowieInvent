# apps/inventory/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CategoriaViewSet,
    ProductoViewSet,
    MovimientoViewSet,
    DashboardView,
    ReporteMovimientosPDFView,
)

router = DefaultRouter()
router.register('categorias', CategoriaViewSet, basename='categoria')
router.register('productos', ProductoViewSet, basename='producto')
router.register('movimientos', MovimientoViewSet, basename='movimiento')

urlpatterns = [
    path('dashboard/', DashboardView.as_view(), name='inventory-dashboard'),
    path(
        'reportes/movimientos.pdf/',
        ReporteMovimientosPDFView.as_view(),
        name='reporte-movimientos-pdf',
    ),
    path('', include(router.urls)),
]
