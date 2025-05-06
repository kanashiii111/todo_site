from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView

from . import views

app_name = 'users'

urlpatterns = [
    path('api/login/', views.api_login, name='api_login'),
    path('api/register/', views.api_register, name='api_register'),
    path('api/get-csrf/', views.login_view_placeholder, name='api_get_csrf'),
    path('api/auth/status/', views.check_auth_status, name='api_auth_status'),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
]
