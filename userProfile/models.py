import datetime
from django.db import models
from django.contrib.auth.models import User
from datetime import timedelta

class Task(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=50)
    description = models.CharField(max_length=50)
    isCompleted = models.BooleanField(default=False)
    subject = models.CharField(max_length=50)
    taskType = models.CharField(max_length=50)
    dateTime_due = models.DateTimeField(default=datetime.date.today)
    xp = models.IntegerField(default=0)
    
    def __str__(self):
        return self.title

class TaskReminder(models.Model):
    task = models.OneToOneField(Task, on_delete=models.CASCADE, related_name='reminder')
    remind_before_days = models.PositiveIntegerField(default=1, help_text="За сколько дней напоминать")
    repeat_interval = models.PositiveIntegerField(
        default=0,
        help_text="Интервал повторения напоминаний (в днях), 0 - не повторять"
    )
    reminder_time = models.TimeField(default='09:00')
    last_reminder_sent = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Напоминание для {self.task.title}"
    
    def next_reminder_datetime(self):
        due_date = self.task.dateTime_due.date()
        reminder_date = due_date - timedelta(days=self.remind_before_days)
        return datetime.combine(reminder_date, self.reminder_time)