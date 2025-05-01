from django.contrib import admin
from .models import Task, TaskReminder

admin.site.register(Task)
admin.site.register(TaskReminder)
