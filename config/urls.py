# config/urls.py
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView
from apps.users.views import EmailTokenObtainPairView, RegisterView

urlpatterns = [
    path('admin/',              admin.site.urls),
    path('api/auth/login/',     EmailTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/refresh/',   TokenRefreshView.as_view(),         name='token_refresh'),
    path('api/auth/register/',  RegisterView.as_view(),             name='register'),
    path('api/tenants/',        include('apps.tenants.urls')),
    path('api/roles/',          include('apps.roles.urls')),
    path('api/users/',          include('apps.users.urls')),
    path('api/inventory/',      include('apps.inventory.urls')),
    path('api/notifications/',  include('apps.notifications.urls')),
]

# En desarrollo, servir los archivos de media (imagenes de productos)
# directamente desde Django. En produccion esto lo hace nginx / S3.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
