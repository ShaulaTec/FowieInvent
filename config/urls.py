"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

# config/urls.py
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
