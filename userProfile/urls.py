from django.urls import path
from . import views

urlpatterns = [
    path('profile/settings/', views.settingsView, name='settings'),
    path('profile/calendar/', views.CalendarView.as_view(), name='calendar'),
    path('profile/tasks/', views.tasksView, name='tasks'),
    path('profile/tasks/task_creation/', views.createTask, name='task_creation'),
]