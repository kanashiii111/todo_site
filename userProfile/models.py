import datetime
from django.db import models
from django.contrib.auth.models import User

class Task(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=50)
    description = models.CharField(max_length=50)
    isCompleted = models.BooleanField(default=False)
    subject = models.CharField(max_length=50)
    taskType = models.CharField(max_length=50)
    dateTime_due = models.DateTimeField(default=datetime.date.today)
    
    def __str__(self):
        return self.title
    
class Event(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField()
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    
    def __str__(self):
        return self.title
