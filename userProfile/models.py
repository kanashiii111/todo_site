from django.db import models
from django.contrib.auth.models import User

class Task(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=50)
    description = models.CharField(max_length=50)
    isCompleted = models.BooleanField(default=False)
    priority = models.IntegerField(default=0)
    tag = models.CharField(max_length=50)
    
    def __str__(self):
        return self.title