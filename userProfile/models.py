import datetime
from django.db import models
from django.contrib.auth.models import User
from datetime import timedelta
from django.utils import timezone

XP_REWARDS = {
    1: 100,
    2: 50,
    3: 25,
    4: 10
}

class Subject(models.Model):
    name = models.CharField(max_length=100)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.name

class TaskType(models.Model):
    name = models.CharField(max_length=100)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.name
    
class Task(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=50)
    description = models.CharField(max_length=50)
    priority = models.IntegerField(default=4)
    isCompleted = models.BooleanField(default=False)
    isExpired = models.BooleanField(default=False)
    wasCompletedBefore = models.BooleanField(default=False)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    taskType = models.ForeignKey(TaskType, on_delete=models.CASCADE)
    dateTime_due = models.DateTimeField(default=timezone.now())
    xp = models.IntegerField(default=0)
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.xp:
            self.xp = self.calc_xp_reward()
        super().save(*args, **kwargs)
    
    def calc_xp_reward(self):
        return XP_REWARDS.get(self.priority, 0)
        
    def complete_task(self):
        if not self.isCompleted:
            self.isCompleted = True
            if not self.wasCompletedBefore:
                from users.models import Profile
                profile = Profile.objects.get(user=self.user)
                profile.xp += self.xp
                profile.save()
                self.wasCompletedBefore = True
                profile.check_level_up()
                
                if profile.telegram_notifications and hasattr(self, 'reminder'):
                    self.reminder.delete()
            
            self.save()
            return True
        return False
    
    def calcIfExpired(self):
        if datetime.date.today >= self.dateTime_due:
            self.isExpired = True

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
        due_date = self.task.dateTime_due
        reminder_date = due_date - timedelta(days=self.remind_before_days)
        reminder_datetime = datetime.datetime.combine(
            reminder_date.date(), 
            self.reminder_time
        )
        if timezone.is_aware(due_date):
            return timezone.make_aware(reminder_datetime, timezone.get_current_timezone())
        return reminder_datetime
