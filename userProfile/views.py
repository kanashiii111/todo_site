## Фронт
import json
from django.http import JsonResponse
from django.views import View
from django.views.decorators.http import require_POST, require_http_methods
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie

from django.shortcuts import get_object_or_404
from .models import Task, TaskReminder
from .forms import SUBJECT_CHOICES, TASKTYPE_CHOICES
from django.contrib.auth import logout, update_session_auth_hash
import calendar
from django.utils.decorators import method_decorator
from .filters import TaskFilter
from datetime import datetime, time, timedelta, date
from django.utils import timezone
from django.db.models import Q
import requests
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from users.models import Profile
import todo_site.settings

@require_POST   
@csrf_exempt
def telegram_webhook(request):
    if request.method == "POST":
        data = json.loads(request.body)
        message = data.get("message", {})
        
        if message.get("text") == "/start":
            chat_id = message["chat"]["id"]
            response_text = (
                f"🔑 Ваш Telegram Chat ID: `{chat_id}`\n\n"
                "1. Скопируйте этот номер\n"
                "2. Вставьте его в поле 'Telegram Chat ID' на сайте\n"
                "3. Сохраните изменения\n\n"
                "Теперь вы будете получать уведомления о задачах!"
            )
            
            requests.post(
                f"https://api.telegram.org/bot{todo_site.settings.TELEGRAM_BOT_TOKEN}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": response_text,
                    "parse_mode": "Markdown"
                }
            )
        
        return JsonResponse({"status": "ok"})
    
    return JsonResponse({"status": "error"}, status=400)

# Настройки

@require_http_methods(["GET", "POST"])
def api_settingsView(request):
    profile = get_object_or_404(Profile, user=request.user)
    
    # Handle JSON requests
    if request.content_type == 'application/json':
        try:
            data = json.loads(request.body) if request.body else {}
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        
        # Process different actions
        if request.method == 'POST':
            action = data.get('action')
            
            if action == 'logout':
                logout(request)
                return JsonResponse({'success': True, 'message': 'Succesfully logged out'})
            
            elif action == 'setTelegramNotis':
                profile.telegram_notifications = not profile.telegram_notifications
                profile.save()
                return JsonResponse({
                    'success': True,
                    'telegram_notifications': profile.telegram_notifications
                })
            
            elif action == 'save_chat_id':
                chat_id = data.get('telegram_chat_id', '').strip()
                if chat_id:
                    profile.telegram_chat_id = chat_id
                    profile.save()
                    return JsonResponse({
                        'success': True,
                        'telegram_chat_id': profile.telegram_chat_id
                    })
                return JsonResponse({'error': 'Invalid chat ID'}, status=400)
            
            elif action == 'edit_profile':
                new_username = data.get('username', '').strip()
                new_status = data.get('status', '').strip()
                
                if new_username:
                    request.user.username = new_username
                    request.user.save()
                
                profile.status = new_status
                profile.save()
                
                return JsonResponse({
                    'success': True,
                    'username': request.user.username,
                    'status': profile.status
                })
            
            elif action == 'change_password':
                old_password = data.get('old_password')
                new_password1 = data.get('new_password1')
                new_password2 = data.get('new_password2')
                
                if not all([old_password, new_password1, new_password2]):
                    return JsonResponse({'error': 'All password fields are required'}, status=400)
                
                if not request.user.check_password(old_password):
                    return JsonResponse({'error': 'Incorrect old password'}, status=400)
                
                if new_password1 != new_password2:
                    return JsonResponse({'error': 'New passwords do not match'}, status=400)
                
                request.user.set_password(new_password1)
                request.user.save()
                update_session_auth_hash(request, request.user)
                
                return JsonResponse({'success': True, 'message': 'Password changed'})
            
            elif action == 'change_email':
                new_email = data.get('new_email', '').strip()
                if not new_email:
                    return JsonResponse({'error': 'Email is required'}, status=400)
                
                request.user.email = new_email
                request.user.save()
                profile.email = new_email
                profile.save()
                
                return JsonResponse({
                    'success': True,
                    'email': request.user.email,
                })
            
            return JsonResponse({'error': 'Invalid action'}, status=400)
        
        # GET request - return current settings
        return JsonResponse({
            'profile': {
                'username': request.user.username,
                'email': request.user.email,
                'status': profile.status,
                'avatar_url': profile.avatar.url if profile.avatar else None,
                'telegram_notifications': profile.telegram_notifications,
                'telegram_chat_id': profile.telegram_chat_id,
            }
        })
 
## Задачи   
    
@require_http_methods(["GET", "POST", "DELETE", "PUT"])
def api_tasksView(request):
    profile = request.user.profile
    
    # JSON API Handling
    if request.content_type == 'application/json':
        try:
            data = json.loads(request.body) if request.body else {}
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        # POST/DELETE Actions
        if request.method in ['POST', 'DELETE', 'PUT']:
            action = data.get('action')
            task_id = data.get('task_id')

            if action == 'createTask':
                try:
                    title = data.get('title')
                    description = data.get('description', '')
                    subject = data.get('subject')
                    task_type = data.get('taskType')
                    date_time_due = data.get('dateTime_due')
                    telegram_notifications = data.get('telegram_notifications', False)
                    
                    # Валидация обязательных полей
                    if not all([title, subject, task_type, date_time_due]):
                        return JsonResponse({'error': 'Missing required fields'}, status=400)
                    
                    # Проверка допустимых значений subject
                    SUBJECT_CHOICES = {
                        "Программирование": "Программирование",
                        "Информатика": "Информатика",
                        "Дискретная математика": "Дискретная математика",
                    }
                    if subject not in SUBJECT_CHOICES:
                        return JsonResponse({
                            'error': f'Invalid subject. Allowed values: {", ".join(SUBJECT_CHOICES.keys())}'
                        }, status=400)
                    
                    # Проверка допустимых значений taskType
                    TASKTYPE_CHOICES = {
                        "Лабораторная работа": "Лабораторная работа",
                        "Практическая работа": "Практическая работа", 
                        "Домашняя работа": "Домашняя работа", 
                        "Экзамен": "Экзамен",
                    }
                    if task_type not in TASKTYPE_CHOICES:
                        return JsonResponse({
                            'error': f'Invalid taskType. Allowed values: {", ".join(TASKTYPE_CHOICES.keys())}'
                        }, status=400)
                    
                    try:
                        due_date = datetime.datetime.strptime(date_time_due, '%d-%m-%YT%H:%M:%S')
                        if timezone.is_aware(due_date):
                            due_date = timezone.make_naive(due_date)
                    except (ValueError, TypeError):
                        return JsonResponse({'error': 'Invalid date format. Use DD-MM-YYYYTHH:MM:SS'}, status=400)
                    
                    # Создаем задачу
                    task = Task.objects.create(
                        user=request.user,
                        title=title,
                        description=description,
                        subject=subject,
                        taskType=task_type,
                        dateTime_due=due_date
                    )
                    
                    response_data = {
                        'success': True,
                        'message': 'Task created successfully',
                        'task': {
                            'id': task.id,
                            'title': task.title,
                            'description': task.description,
                            'subject': task.subject,
                            'taskType': task.taskType,
                            'dateTime_due': task.dateTime_due.isoformat(),
                            'isCompleted': task.isCompleted
                        }
                    }
                    
                    # Обработка напоминаний
                    if telegram_notifications and profile.telegram_notifications:
                        remind_before_days = data.get('remind_before_days', 1)
                        repeat_interval = data.get('repeat_interval', 0)
                        reminder_time = data.get('reminder_time', '09:00')
                        
                        try:
                            reminder_time_obj = datetime.datetime.strptime(reminder_time, '%H:%M').time()
                        except ValueError:
                            reminder_time_obj = datetime.time(9, 0)
                        
                        # Создаем напоминание
                        TaskReminder.objects.create(
                            task=task,
                            remind_before_days=remind_before_days,
                            repeat_interval=repeat_interval,
                            reminder_time=reminder_time_obj
                        )
                        
                        response_data['task']['reminder'] = {
                            'remind_before_days': remind_before_days,
                            'repeat_interval': repeat_interval,
                            'reminder_time': reminder_time
                        }
                        response_data['message'] = 'Task with reminder created successfully'
                    
                    return JsonResponse(response_data)
                    
                except Exception as e:
                    return JsonResponse({'error': f'Task creation failed: {str(e)}'}, status=500)
            elif action == 'delete_task':
                task = get_object_or_404(Task, id=task_id, user=request.user)
                task.delete()
                return JsonResponse({'success': True, 'message': 'Task deleted'})
            elif action == "edit_task":
                task = get_object_or_404(Task, id=task_id, user=request.user)
    
                try:
                    # Получаем обновленные данные
                    new_title = data.get('title', task.title)
                    new_description = data.get('description', task.description)
                    new_subject = data.get('subject', task.subject)
                    new_task_type = data.get('taskType', task.taskType)
                    new_date_time_due = data.get('dateTime_due', task.dateTime_due.isoformat())
                    telegram_notifications = data.get('telegram_notifications', False)
                    
                    # Проверка допустимых значений subject
                    SUBJECT_CHOICES = {
                        "Программирование": "Программирование",
                        "Информатика": "Информатика",
                        "Дискретная математика": "Дискретная математика",
                    }
                    if new_subject not in SUBJECT_CHOICES:
                        return JsonResponse({
                            'error': f'Invalid subject. Allowed values: {", ".join(SUBJECT_CHOICES.keys())}'
                        }, status=400)
                    
                    # Проверка допустимых значений taskType
                    TASKTYPE_CHOICES = {
                        "Лабораторная работа": "Лабораторная работа",
                        "Практическая работа": "Практическая работа", 
                        "Домашняя работа": "Домашняя работа", 
                        "Экзамен": "Экзамен",
                    }
                    if new_task_type not in TASKTYPE_CHOICES:
                        return JsonResponse({
                            'error': f'Invalid taskType. Allowed values: {", ".join(TASKTYPE_CHOICES.keys())}'
                        }, status=400)

                    # Обновляем основные поля задачи
                    task.title = new_title
                    task.description = new_description
                    task.subject = new_subject
                    task.taskType = new_task_type
                    
                    # Обрабатываем дату
                    try:
                        if isinstance(new_date_time_due, str):
                            due_date = datetime.datetime.strptime(new_date_time_due, '%d-%m-%YT%H:%M:%S')
                            if timezone.is_aware(due_date):
                                due_date = timezone.make_naive(due_date)
                            task.dateTime_due = due_date
                    except (ValueError, TypeError) as e:
                        return JsonResponse({'error': f'Invalid date format: {str(e)}'}, status=400)
                    
                    # Сохраняем задачу
                    task.save()
                    
                    response_data = {
                        'success': True,
                        'message': 'Task updated successfully',
                        'task': {
                            'id': task.id,
                            'title': task.title,
                            'description': task.description,
                            'subject': task.subject,
                            'taskType': task.taskType,
                            'dateTime_due': task.dateTime_due.isoformat(),
                            'isCompleted': task.isCompleted
                        }
                    }
                    
                    # Обработка напоминаний
                    if hasattr(task, 'reminder'):
                        current_reminder = task.reminder
                        
                        if telegram_notifications and profile.telegram_notifications:
                            # Обновляем существующее напоминание
                            remind_before_days = data.get('remind_before_days', current_reminder.remind_before_days)
                            repeat_interval = data.get('repeat_interval', current_reminder.repeat_interval)
                            reminder_time = data.get('reminder_time', current_reminder.reminder_time.strftime('%H:%M'))
                            
                            try:
                                reminder_time_obj = datetime.datetime.strptime(reminder_time, '%H:%M').time()
                            except ValueError:
                                reminder_time_obj = datetime.time(9, 0)
                            
                            current_reminder.remind_before_days = remind_before_days
                            current_reminder.repeat_interval = repeat_interval
                            current_reminder.reminder_time = reminder_time_obj
                            current_reminder.save()
                            
                            response_data['task']['reminder'] = {
                                'remind_before_days': remind_before_days,
                                'repeat_interval': repeat_interval,
                                'reminder_time': reminder_time
                            }
                        else:
                            # Удаляем напоминание, если уведомления отключены
                            current_reminder.delete()
                            response_data['message'] = 'Task updated (reminder removed)'
                    elif telegram_notifications and profile.telegram_notifications:
                        # Создаем новое напоминание
                        remind_before_days = data.get('remind_before_days', 1)
                        repeat_interval = data.get('repeat_interval', 0)
                        reminder_time = data.get('reminder_time', '09:00')
                        
                        try:
                            reminder_time_obj = datetime.datetime.strptime(reminder_time, '%H:%M').time()
                        except ValueError:
                            reminder_time_obj = datetime.time(9, 0)
                        
                        TaskReminder.objects.create(
                            task=task,
                            remind_before_days=remind_before_days,
                            repeat_interval=repeat_interval,
                            reminder_time=reminder_time_obj
                        )
                        
                        response_data['task']['reminder'] = {
                            'remind_before_days': remind_before_days,
                            'repeat_interval': repeat_interval,
                            'reminder_time': reminder_time
                        }
                        response_data['message'] = 'Task updated with new reminder'
                    
                    return JsonResponse(response_data)
                    
                except Exception as e:
                    return JsonResponse({'error': f'Task update failed: {str(e)}'}, status=500)

            elif action == 'toggle_completeTask':
                task = get_object_or_404(Task, id=task_id, user=request.user)
                if not task.isCompleted:
                    task.complete_task()
                else:
                    task.isCompleted = False
                    task.save()
                return JsonResponse({
                    'success': True,
                    'isCompleted': task.isCompleted
                })

        # GET Request - Return tasks data
        search_query = request.GET.get('search', '')
        tasks = Task.objects.filter(user=request.user)

        if search_query:
            tasks = tasks.filter(
                Q(title__icontains=search_query) | 
                Q(description__icontains=search_query)
            )

        task_filter = TaskFilter(request.GET, queryset=Task.objects.filter(user=request.user))
        tasks = task_filter.qs.order_by('dateTime_due')

        now = timezone.now()
        today = now.date()
        days = []

        for i in range(7):
            current_date = today + timedelta(days=i)
            day_name = "Сегодня" if i == 0 else "Завтра" if i == 1 else current_date.strftime("%d.%m.%Y")
            
            start_of_day = datetime.combine(current_date, time.min, tzinfo=timezone.get_current_timezone())
            end_of_day = datetime.combine(current_date, time.max, tzinfo=timezone.get_current_timezone())
            
            day_tasks = []
            for task in tasks:
                task_due_local = timezone.localtime(task.dateTime_due)
                if start_of_day <= task_due_local <= end_of_day:
                    day_tasks.append({
                        'id': task.id,
                        'title': task.title,
                        'description': task.description,
                        'isCompleted': task.isCompleted,
                        'due_date': task.dateTime_due.isoformat(),
                        'subject': task.subject,
                        'task_type': task.taskType
                    })
            
            days.append({
                'date': current_date.strftime("%Y-%m-%d"),
                'name': day_name,
                'tasks': day_tasks
            })

        return JsonResponse({
            'days': days,
            'subject_choices': dict(SUBJECT_CHOICES),
            'task_type_choices': dict(TASKTYPE_CHOICES),
            'profile': {
                'username': profile.user.username,
                'avatar_url': profile.avatar.url if profile.avatar else None
            }
        })

def get_day_tasks(request):
    date_str = request.GET.get('date')
    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Invalid date format'}, status=400)
    
    start_of_day = timezone.make_aware(datetime.combine(selected_date, time.min))
    end_of_day = timezone.make_aware(datetime.combine(selected_date, time.max))
    
    tasks = Task.objects.filter(
        user=request.user,
        dateTime_due__gte=start_of_day,
        dateTime_due__lte=end_of_day
    ).order_by('dateTime_due')
    
    tasks_data = [
        {
            'id': task.id,
            'title': task.title,
            'dateTime_due': task.dateTime_due.isoformat(),
        }
        for task in tasks
    ]
    
    return JsonResponse({'tasks': tasks_data})
    
def get_task_data(request, task_id):
    task = get_object_or_404(Task, id=task_id, user=request.user)
    try:
        reminder = task.reminder
        reminder_data = {
            'remind_before_days': reminder.remind_before_days,
            'repeat_reminder': reminder.repeat_interval,
            'reminder_time': reminder.reminder_time.strftime('%H:%M'),
        }
    except TaskReminder.DoesNotExist:
        reminder_data = {
            'remind_before_days': 1,
            'repeat_reminder': 0,
            'reminder_time': '09:00',
        }
    return JsonResponse({
        'title': task.title,
        'description': task.description,
        'subject': task.subject,
        'taskType': task.taskType,
        'dateTime_due': task.dateTime_due.isoformat(),
        **reminder_data
    })

## Календарь

@method_decorator(require_http_methods(["GET"]), name='dispatch')
class api_calendarView(View):
    def get(self, request, *args, **kwargs):
        # JSON API Handling
        if request.content_type == 'application/json':
            return self.handle_json_request(request)
    
    def handle_json_request(self, request):
        try:
            selected_date = self.get_date(request.GET.get('month'))
            
            # Get tasks for the user
            tasks = Task.objects.filter(
                user=request.user
            ).select_related('user').order_by('dateTime_due')
            
            # Prepare calendar data
            cal = calendar.Calendar()
            month_days = cal.monthdatescalendar(selected_date.year, selected_date.month)
            
            # Format tasks data
            tasks_list = []
            for task in tasks:
                local_due = timezone.localtime(task.dateTime_due)
                task_data = {
                    'id': task.id,
                    'title': task.title,
                    'description': task.description,
                    'subject': task.subject,
                    'taskType': task.taskType,
                    'dateTime_due': task.dateTime_due.isoformat(),
                    'local_date': local_due.strftime('%Y-%m-%d'),
                    'isCompleted': task.isCompleted,
                    'xp': task.xp
                }
                if hasattr(task, 'reminder'):
                    task_data['reminder'] = {
                        'remind_before_days': task.reminder.remind_before_days,
                        'repeat_interval': task.reminder.repeat_interval,
                        'reminder_time': task.reminder.reminder_time.strftime('%H:%M')
                    }
                tasks_list.append(task_data)
            
            # Prepare calendar structure
            calendar_data = []
            for week in month_days:
                week_data = []
                for day in week:
                    day_tasks = [t for t in tasks_list if t['local_date'] == day.strftime('%Y-%m-%d')]
                    week_data.append({
                        'date': day.strftime('%Y-%m-%d'),
                        'day_name': day.strftime('%A'),
                        'day_number': day.day,
                        'is_current_month': day.month == selected_date.month,
                        'tasks': day_tasks
                    })
                calendar_data.append(week_data)
            
            profile = request.user.profile
            today = timezone.localtime(timezone.now()).date()
            
            return JsonResponse({
                'success': True,
                'calendar': calendar_data,
                'navigation': {
                    'prev_month': self.prev_month(selected_date),
                    'next_month': self.next_month(selected_date),
                    'current_month': f'{selected_date.year}-{selected_date.month}'
                },
                'current_date': {
                    'month_name': self.get_month_name(selected_date),
                    'year': selected_date.year
                },
                'today': today.strftime('%Y-%m-%d'),
                'user_profile': {
                    'username': profile.user.username,
                    'avatar_url': profile.avatar.url if profile.avatar else None,
                    'xp': profile.xp,
                    'level': profile.level
                },
                'choices': {
                    'subjects': dict(SUBJECT_CHOICES),
                    'task_types': dict(TASKTYPE_CHOICES)
                }
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    def get_date(self, req_month):
        """Parse date from request parameter or return current date"""
        if req_month:
            year, month = map(int, req_month.split('-'))
            return date(year, month, day=1)
        return timezone.localtime(timezone.now()).date()
    
    def prev_month(self, d):
        """Generate URL parameter for previous month"""
        first = d.replace(day=1)
        prev_month = first - timedelta(days=1)
        return f'{prev_month.year}-{prev_month.month}'
    
    def next_month(self, d):
        """Generate URL parameter for next month"""
        days_in_month = calendar.monthrange(d.year, d.month)[1]
        last = d.replace(day=days_in_month)
        next_month = last + timedelta(days=1)
        return f'{next_month.year}-{next_month.month}'
    
    def get_month_name(self, date_obj):
        """Return localized month name"""
        month_names = [
            'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
            'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
        ]
        return month_names[date_obj.month - 1]