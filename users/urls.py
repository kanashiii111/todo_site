from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('login/', views.loginUser, name='login'),
    path('register/', views.registerUser, name='register')
]
