from django.db import models
from django.contrib.auth.models import User
from django.dispatch import receiver
from django.db.models.signals import post_save
from userProfile.models import Task
import hashlib

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    email = models.EmailField(unique=True, default='')
    status = models.CharField(default='#Завтра точно начну', blank=True, null=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    tasks = models.ManyToManyField(Task)
    telegram_chat_id = models.CharField(max_length=50, blank=True, null=True)
    telegram_notifications = models.BooleanField(default=False)
    xp = models.IntegerField(default=0)
    level = models.IntegerField(default=0)
    
    def __str__(self):
        return self.user.username
    
    @property
    def level(self):
        return self.xp // 100 + 1

    @property
    def xp_percentage(self):
        xp_needed_for_level = self.xp_for_next_status()
        current_lvl_xp = self.xp % xp_needed_for_level
        return int((current_lvl_xp / xp_needed_for_level) * 100) if xp_needed_for_level > 0 else 0
    
    def get_avatar_url(self):
        if self.avatar:
            return self.avatar.url
        return self.get_gravatar_url()

    def get_gravatar_url(self):
        email_hash = hashlib.md5(self.email.lower().encode('utf-8')).hexdigest()
        return f"https://www.gravatar.com/avatar/{email_hash}?d=identicon"
    
    def get_status(self):
        statuses = [
            (0, "#Завтра точно начну"),
            (100, "#Начал и бросил"),
            (300, "#Делаю когда вспомню"),
            (600, "#Старатель"),
            (1000, "#Хвостоуничтожитель3000"),
            (1500, "#Неостанавливаемый"),
            (3000, "#Машина для выполнения задач")
        ]
        
        current_status = "#Завтра точно начну"
        for exp, status in sorted(statuses, key=lambda x: x[0]):
            if self.xp >= exp:
                current_status = status
        return current_status
    
    def xp_for_next_status(self):
        statuses = [
            (0, "#Завтра точно начну"),
            (100, "#Начал и бросил"),
            (300, "#Делаю когда вспомню"),
            (600, "#Старатель"),
            (1000, "#Хвостоуничтожитель3000"),
            (1500, "#Неостанавливаемый"),
            (3000, "#Машина для выполнения задач")
        ]
        for exp, status in sorted(statuses, key=lambda x: x[0]):
            if self.xp < exp:
                return exp
        
        return statuses[-1][0]  # Возвращаем максимальный порог

    def add_xp(self, amount):
        self.xp += amount
        self.save()
        return self.check_level_up()

    def check_level_up(self):
        old_level = self.level
        new_level = self.xp // 100 + 1
        if new_level > old_level:
            self.status = self.get_status()
            self.save()
            return True
        return False

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance, email=instance.email)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()
    else:
        Profile.objects.create(user=instance, email=instance.email)