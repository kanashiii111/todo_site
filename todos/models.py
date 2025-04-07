from django.db import models

class todo(models.Model):
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=100)
    isCompleted = models.BooleanField(default=False)
    priority = models.IntegerField(default=0)
    tag = models.CharField(max_length=100)
    
    def __str__(self):
        return self.name
    
