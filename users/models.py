from django.db import models
from django.contrib.auth.models import User
from django.dispatch import receiver
from django.db.models.signals import post_save
from userProfile.models import Task

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    status = models.CharField(default='', blank=True, null=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    tasks = models.ManyToManyField(Task)
    telegram_chat_id = models.CharField(max_length=50, blank=True, null=True)
    telegram_notifications = models.BooleanField(default=False)
    xp = models.IntegerField(default=0)
    
    def __str__(self):
        return self.user.username
    
    @property
    def level(self):
        return self.xp // 100 + 1

    @property
    def xp_percentage(self):
        xp_needed_for_level = 100
        current_lvl_xp = self.xp % xp_needed_for_level
        return int((current_lvl_xp / xp_needed_for_level) * 100) if xp_needed_for_level > 0 else 0
        
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()
