from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from django.utils import timezone
import requests
from django.conf import settings
import logging
from django_apscheduler.jobstores import DjangoJobStore, register_events
from django.db import close_old_connections
import time
from django.db.utils import OperationalError
from datetime import timedelta

logger = logging.getLogger(__name__)

# Глобальный экземпляр планировщика
scheduler = BackgroundScheduler()
scheduler.add_jobstore(DjangoJobStore(), "default")

def send_reminder(reminder_id):
    from .models import TaskReminder
    max_retries = 3
    retry_delay = 0.1
    
    for attempt in range(max_retries):
        try:
            close_old_connections()  # Закрываем старые соединения
            reminder = TaskReminder.objects.get(id=reminder_id)
            task = reminder.task
            local_due = timezone.localtime(task.dateTime_due)
            
            message = (
                f"⏰ Напоминание для задачи: {task.title}\n"
                f"📅 Срок выполнения: {local_due.strftime('%d.%m.%Y %H:%M')}\n"
                f"📝 {task.description or 'Описание'}\n"
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
                next_possible_reminder = reminder.last_reminder_sent + timedelta(days=reminder.repeat_interval)
                if next_possible_reminder >= reminder.task.dateTime_due:
                    reminder.is_active = False
                if reminder.remind_before_days != 0:
                    reminder.is_active = False
                elif reminder.repeat_interval > 0:
                    schedule_next_reminder(reminder)
                else:
                    reminder.is_active = False
                reminder.save()
            
            break  # Успешное выполнение, выходим из цикла
            
        except OperationalError as e:
            if attempt == max_retries - 1:
                logger.error(f"Ошибка отправки (попытки исчерпаны): {e}")
            else:
                time.sleep(retry_delay)
        except Exception as e:
            logger.error(f"Ошибка отправки: {e}")
            break

def schedule_next_reminder(reminder):
    remind_time = reminder.next_reminder_datetime()
    job_id = f"reminder_{reminder.id}_{remind_time.timestamp()}"
    
    scheduler.add_job(
        send_reminder,
        trigger=DateTrigger(remind_time),
        args=[reminder.id],
        id=job_id,
        replace_existing=True,
    )
    register_events(scheduler)

def check_and_schedule_reminders():
    from .models import TaskReminder
    max_retries = 3
    retry_delay = 0.1
    
    for attempt in range(max_retries):
        try:
            close_old_connections()
            now = timezone.localtime(timezone.now())
            logger.info(f"Начало проверки напоминаний в {now}")
            
            reminders = list(TaskReminder.objects.filter(is_active=True).select_related('task'))
            
            for reminder in reminders:
                try:
                    remind_time = reminder.next_reminder_datetime()
                    if now >= remind_time:
                        logger.info(f"Немедленная отправка для задачи {reminder.task.id}!")
                        send_reminder(reminder.id)
                    else:
                        logger.info(f"Планирование для задачи {reminder.task.id} на {remind_time}")
                        schedule_next_reminder(reminder)
                        
                except Exception as e:
                    logger.error(f"Ошибка обработки напоминания {reminder.id}: {str(e)}")
            
            break  # Успешное выполнение
            
        except OperationalError as e:
            if attempt == max_retries - 1:
                logger.error(f"Ошибка проверки напоминаний (попытки исчерпаны): {e}")
            else:
                time.sleep(retry_delay)
        except Exception as e:
            logger.error(f"Критическая ошибка: {str(e)}")
            break