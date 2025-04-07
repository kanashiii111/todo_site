from django.urls import path
from . import views
from .views import todoListCreateView, todoRetrieveUpdateDestroyView

urlpatterns = [
    path('todos/', todoListCreateView.as_view(), name='todo-list'),
    path('todos/<int:pk>/', todoRetrieveUpdateDestroyView.as_view(), name='todo-detail')
]
