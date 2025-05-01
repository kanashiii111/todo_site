from celery import shared_task
from django.utils import timezone
from .models import TaskReminder
import requests
from django.conf import settings
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

@shared_task(bind=True, max_retries=3)
def send_reminder(self, reminder_id):
    try:
        reminder = TaskReminder.objects.get(id=reminder_id)
        task = reminder.task
        local_due = timezone.localtime(task.dateTime_due)
        
        message = (
            f"⏰ Напоминание: {task.title}\n"
            f"📅 Срок выполнения: {local_due.strftime('%d.%m.%Y %H:%M')}\n"
            f"⏱ Время уведомления: {reminder.reminder_time.strftime('%H:%M')}\n"
            f"📝 {task.description or '-'}\n"
        )
        
        if task.user.profile.telegram_notifications and task.user.profile.telegram_chat_id:
            url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {
                'chat_id': task.user.profile.telegram_chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }
            requests.post(url, json=payload)
            
            reminder.last_reminder_sent = timezone.now()
            if reminder.repeat_interval > 0:
                new_days = reminder.remind_before_days + reminder.repeat_interval
                if new_days < (task.dateTime_due - timezone.now()).days:
                    reminder.remind_before_days = new_days
                else:
                    reminder.is_active = False
            else:
                reminder.is_active = False
            reminder.save()
            
    except Exception as e:
        logger.error(f"Ошибка отправки: {e}")
        self.retry(exc=e, countdown=300)
        
@shared_task
def check_reminders():
    from .models import TaskReminder
    import logging
    logger = logging.getLogger(__name__)
    now = timezone.localtime(timezone.now())
    logger.info(f"Начало проверки напоминаний в {now}")
    
    for reminder in TaskReminder.objects.filter(is_active=True):
        remind_time = reminder.next_reminder_datetime()
        logger.info(f"Проверка задачи {reminder.task.id}: {remind_time} (сейчас {now})")
        
        if now >= remind_time:
            logger.info(f"Напоминание для задачи {reminder.task.id} должно быть отправлено!")
            send_reminder.delay(reminder.id)