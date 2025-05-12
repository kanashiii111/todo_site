import logging
from django.apps import AppConfig
import threading
from django.conf import settings

logger = logging.getLogger(__name__)

class UserprofileConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'userProfile'

    def ready(self):
        if settings.DEBUG:
            logger.info("Инициализация приложения userProfile")
        
        # Запускаем планировщик в отдельном потоке после полной загрузки Django
        threading.Thread(
            target=self._delayed_scheduler_start,
            daemon=True
        ).start()

    def _delayed_scheduler_start(self):
        """Отложенный запуск планировщика после полной инициализации Django"""
        import time
        from django.db import connection
        
        while True:
            try:
                connection.ensure_connection()
                break
            except Exception:
                time.sleep(0.1)
        
        if settings.DEBUG:
            logger.info("Запуск планировщика...")
        
        from apscheduler.schedulers.background import BackgroundScheduler
        from django_apscheduler.jobstores import DjangoJobStore
        from .tasks import check_and_schedule_reminders

        scheduler = BackgroundScheduler()
        scheduler.add_jobstore(DjangoJobStore(), "default")
        
        scheduler.add_job(
            check_and_schedule_reminders,
            trigger='interval',
            minutes=1,
            id="check_reminders",
            replace_existing=True,
        )
        
        scheduler.start()
        
        if settings.DEBUG:
            logger.info("Планировщик успешно запущен")