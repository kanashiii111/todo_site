from django.contrib import admin
from .models import Task, TaskReminder, Subject, TaskType
    
admin.site.register(Task)
admin.site.register(TaskReminder)
admin.site.register(Subject)
admin.site.register(TaskType)
