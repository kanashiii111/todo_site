from django.urls import path
from . import views

urlpatterns = [
    path('profile/settings/', views.settingsView, name='settings'),
    path('profile/calendar/', views.calendarView, name='calendar'),
    path('profile/tasks/', views.tasksView, name='tasks')
]