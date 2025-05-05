from django.urls import path
from . import views
from .views import api_calendarView

app_name = 'userProfile'

urlpatterns = [
    path('api/tasks/<int:pk>', views.api_tasksView, name='api_tasks_view'),
    path('api/settings/', views.api_settingsView, name='api_settings_view'),
    path('api/calendar/', api_calendarView.as_view(), name='api_calendar_view'),
    path('get-task-data/<int:task_id>/', views.get_task_data, name='get_task_data'),
    path('get-day-tasks/', views.get_day_tasks, name='get_day_tasks'),
    path("webhook/telegram/", views.telegram_webhook, name="telegram_webhook"),
]