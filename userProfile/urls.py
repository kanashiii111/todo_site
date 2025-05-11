from django.urls import path
from . import views
from .views import api_calendarView

app_name = 'userProfile'

urlpatterns = [

    # Задачи

    path('api/tasks/view_tasks/', views.api_tasksView, name='api_tasks_view'),
    path('api/tasks/view_task/<int:task_id>/', views.api_taskView, name='api_task_view'),
    path(
        'api/tasks/view_selected_date_tasks/', 
        views.api_selected_date_taskView, 
        name='api_selected_date_task_view'
    ),
    path('api/tasks/create_task/', views.api_taskCreate, name='api_task_create'),
    path('api/tasks/delete_task/<int:task_id>/', views.api_taskDelete, name='api_task_delete'),
    path('api/tasks/edit_task/<int:task_id>/', views.api_taskEdit, name='api_task_edit'),
    path(
        'api/tasks/toggle_complete_task/<int:task_id>/', 
        views.api_task_toggle_complete, 
        name='api_task_toggle_complete'
    ),

    # Настройки

    path('api/settings/view_settings/', views.api_settingsView, name='api_settings_view'),
    path('api/settings/logout/', views.api_settingsLogout, name='api_settings_logout'),
    path(
        'api/settings/toggle_telegram_notifications/', 
        views.api_settings_toggle_telegram_notifications, 
        name='api_settings_toggle_telegram_notifications'
    ),
    path('api/settings/save_chat_id/', views.api_settings_save_chat_id, name='api_settings_save_chat_id'),
    path('api/settings/edit_profile/', views.api_settings_edit_profile, name='api_settings_edit_profile'),

    # Календарь

    path('api/calendar/view_calendar/', api_calendarView.as_view(), name='api_calendar_view'),
    
    # Теги

    path('api/tags/view_tags/', views.api_tagsView, name='api_tags_view'),
    path('api/tags/view_tag/', views.api_tagView, name='api_tag_view'),
    path('api/tags/create_tags/', views.api_tagsCreate, name='api_tags_create'),
    path('api/tags/delete_tag/', views.api_tagsDelete, name='api_tags_delete'),
    path('api/tags/edit_tag/', views.api_tagEdit, name='api_tag_edit'),

    # Вебхук
    
    path("webhook/telegram/", views.telegram_webhook, name="telegram_webhook"),
]