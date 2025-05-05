from django.urls import path

from . import views

app_name = 'users'

urlpatterns = [
    path('', views.home_redirect, name='home_redirect'),
    path('login/', views.loginUser, name='login'),
    path('register/', views.registerUser, name='register'),
    path('api/login/', views.api_login, name='api_login'),
    path('api/logout/', views.api_logout, name='api_logout'),
    path('api/get-csrf/', views.login_view_placeholder, name='api_get_csrf'),
    path('api/auth/status/', views.check_auth_status, name='api_auth_status'),
]
