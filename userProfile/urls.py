from django.urls import path
from . import views

urlpatterns = [
    path('profile/<slug:page_slug>/', views.profile_page_view, name='profile_page')
]