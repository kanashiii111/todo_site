from django.db import models

class Task(models.Model):
    title = models.CharField(max_length=50)
    description = models.CharField(max_length=50)
    isCompleted = models.BooleanField(default=False)
    priority = models.IntegerField(default=0)
    tag = models.CharField(max_length=50)
    
    def __str__(self):
        return self.title
