from django.contrib import admin
from .models import Task, TaskReminder, Tag

admin.site.register(Task)
admin.site.register(TaskReminder)
admin.site.register(Tag)
