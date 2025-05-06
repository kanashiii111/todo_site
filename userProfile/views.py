## Фронт
import json
from django.http import Http404, JsonResponse
from django.views import View
from django.views.decorators.http import require_POST, require_http_methods
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.core.files.base import ContentFile
from django.contrib.auth import authenticate, update_session_auth_hash, logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
import base64

from django.shortcuts import get_object_or_404
from .models import Task, TaskReminder
from .forms import SUBJECT_CHOICES, TASKTYPE_CHOICES
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

@require_http_methods(["GET"])
def api_settingsView(request):
    profile = get_object_or_404(Profile, user=request.user)

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

@require_http_methods(["POST"])
def api_settingsLogout(request):
    logout(request)
    return JsonResponse({'success': True, 'message': 'Successfully logged out'})
 
@require_http_methods(["PATCH"])
def api_settings_toggle_telegram_notifications(request):
    profile = request.user.profile
    profile.telegram_notifications = not profile.telegram_notifications
    profile.save()
    return JsonResponse({
        'success': True,
        'telegram_notifications': profile.telegram_notifications
    })
    
@require_http_methods(["PATCH"])
def api_settings_save_chat_id(request):
    profile = request.user.profile
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    chat_id = data.get('telegram_chat_id', profile.telegram_chat_id)
    if chat_id:
        profile.telegram_chat_id = chat_id
        profile.save()
        return JsonResponse({
            'success': True,
            'telegram_chat_id': profile.telegram_chat_id
        })
    return JsonResponse({'error': 'Invalid chat ID'}, status=400)

@require_http_methods(["PATCH"])
def api_settings_edit_profile(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)

    user = request.user
    profile = user.profile
    response_data = {'success': True}

    try:
        # Для обработки multipart/form-data (аватар) и JSON (остальные данные)
        if request.content_type == 'multipart/form-data':
            data = request.POST.dict()
            files = request.FILES
        else:
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({'error': 'Invalid JSON'}, status=400)
            files = None
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

    # Обновление аватара
    if 'avatar' in request.FILES:
        profile.avatar = request.FILES['avatar']
        response_data['avatar_url'] = profile.avatar.url if profile.avatar else None
    elif 'avatar' in data and data['avatar'] is None:
        # Удаление аватара
        profile.avatar.delete(save=False)
        response_data['avatar_url'] = None
    elif 'avatar' in data and isinstance(data['avatar'], str) and data['avatar'].startswith('data:image'):
        # Base64 изображение
        try:
            format, imgstr = data['avatar'].split(';base64,')
            ext = format.split('/')[-1]
            avatar_file = ContentFile(base64.b64decode(imgstr), name=f'avatar.{ext}')
            profile.avatar.save(avatar_file.name, avatar_file, save=False)
            response_data['avatar_url'] = profile.avatar.url
        except Exception as e:
            return JsonResponse({'error': f'Invalid avatar image: {str(e)}'}, status=400)

    # Обновление никнейма
    if 'username' in data:
        new_username = data['username'].strip()
        if new_username and new_username != user.username:
            if len(new_username) < 3:
                return JsonResponse({'error': 'Username too short (min 3 chars)'}, status=400)
            user.username = new_username
            response_data['username'] = new_username

    # Обновление почты
    if 'email' in data:
        new_email = data['email'].strip()
        if new_email and new_email != user.email:
            if '@' not in new_email:
                return JsonResponse({'error': 'Invalid email format'}, status=400)
            user.email = new_email
            response_data['email'] = new_email

    # Обновление пароля
    if 'password' in data and 'current_password' in data:
        current_password = data['current_password']
        new_password = data['password']
        
        if not authenticate(username=user.username, password=current_password):
            return JsonResponse({'error': 'Current password is incorrect'}, status=400)
        
        try:
            validate_password(new_password, user)
        except ValidationError as e:
            return JsonResponse({'error': ' '.join(e.messages)}, status=400)
        
        user.set_password(new_password)
        update_session_auth_hash(request, user)
        response_data['password_changed'] = True

    # Сохранение изменений
    try:
        user.save()
        profile.save()
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse(response_data)

## Задачи   
    
SUBJECT_CHOICES = {
    "Программирование": "Программирование",
    "Информатика": "Информатика",
    "Дискретная математика": "Дискретная математика",
}

TASKTYPE_CHOICES = {
    "Лабораторная работа": "Лабораторная работа",
    "Практическая работа": "Практическая работа", 
    "Домашняя работа": "Домашняя работа", 
    "Экзамен": "Экзамен",
}

@require_http_methods(["GET"])
def api_tasksView(request):
    profile = request.user.profile

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
        'profile': profile.user.username, 
        'days': days,
        'subject_choices': dict(SUBJECT_CHOICES),
        'task_type_choices': dict(TASKTYPE_CHOICES),
    })
    
@require_http_methods(["POST"])
def api_taskCreate(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    profile = request.user.profile

    try:
        title = data.get('title')
        description = data.get('description', '')
        subject = data.get('subject')
        task_type = data.get('taskType')
        date_time_due = data.get('dateTime_due')
        telegram_notifications = data.get('telegram_notifications', False)
        
        # Валидация обязательных полей
        if not all([title, subject, task_type, date_time_due]):
            return JsonResponse({'error': 'Missing required fields: title, subject, taskType, dateTime_due'}, status=400)
        
        # Проверка допустимых значений subject
        if subject not in SUBJECT_CHOICES:
            return JsonResponse({
                'error': f'Invalid subject. Allowed values: {", ".join(SUBJECT_CHOICES.keys())}'
            }, status=400)
        
        # Проверка допустимых значений taskType
        if task_type not in TASKTYPE_CHOICES:
            return JsonResponse({
                'error': f'Invalid taskType. Allowed values: {", ".join(TASKTYPE_CHOICES.keys())}'
            }, status=400)
        
        try:
            due_date = datetime.strptime(date_time_due, '%d-%m-%YT%H:%M')
            if timezone.is_aware(due_date):
                due_date = timezone.make_naive(due_date)
        except (ValueError, TypeError):
            return JsonResponse({'error': 'Invalid date format. Use DD-MM-YYYYTHH:MM'}, status=400)
        
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
            'profile' : profile.user.username,
            'task': {
                'id': task.id,
                'title': task.title,
                'description': task.description,
                'subject': task.subject,
                'taskType': task.taskType,
                'dateTime_due': task.dateTime_due.isoformat(),
                'isCompleted': task.isCompleted
            },
        }
        
        # Обработка напоминаний
        if telegram_notifications and profile.telegram_notifications:
            remind_before_days = data.get('remind_before_days', 1)
            repeat_interval = data.get('repeat_interval', 0)
            reminder_time = data.get('reminder_time', '09:00')
            
            try:
                reminder_time_obj = datetime.strptime(reminder_time, '%H:%M').time()
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

@require_http_methods(["DELETE"])
def api_taskDelete(request, task_id):
    try:
        task = get_object_or_404(Task, id=task_id, user=request.user)
        task.delete()
        return JsonResponse({
            'success': True, 
            'message': 'Task deleted'
        })
    except Http404:
        return JsonResponse({
            'success': False, 
            'message': 'Task by this id is nonexistent'
        })
    
@require_http_methods(["PUT"])
def api_taskEdit(request, task_id):
    try:
        task = get_object_or_404(Task, id=task_id, user=request.user)
    except Http404:
        return JsonResponse({
            'error': 'Task by this id is nonexistent'
        })
    profile = request.user.profile

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    try:
        # Получаем обновленные данные
        new_title = data.get('title', task.title)
        new_description = data.get('description', task.description)
        new_subject = data.get('subject', task.subject)
        new_task_type = data.get('taskType', task.taskType)
        new_date_time_due = data.get('dateTime_due', task.dateTime_due)
        telegram_notifications = data.get('telegram_notifications', False)
        
        # Проверка допустимых значений subject

        if new_subject not in SUBJECT_CHOICES:
            return JsonResponse({
                'error': f'Invalid subject. Allowed values: {", ".join(SUBJECT_CHOICES.keys())}'
            }, status=400)
        
        # Проверка допустимых значений taskType

        if new_task_type not in TASKTYPE_CHOICES:
            return JsonResponse({
                'error': f'Invalid taskType. Allowed values: {", ".join(TASKTYPE_CHOICES.keys())}'
            }, status=400)
        
        # Обрабатываем дату

        try:
            if isinstance(new_date_time_due, str):
                due_date = datetime.strptime(new_date_time_due, '%d-%m-%YT%H:%M')
                if timezone.is_aware(due_date):
                    due_date = timezone.make_naive(due_date)
                task.dateTime_due = due_date
        except (ValueError, TypeError) as e:
            return JsonResponse({'error': f'Invalid date format: {str(e)}'}, status=400)
        
        task.title = new_title
        task.description = new_description
        task.subject = new_subject
        task.taskType = new_task_type
        task.save()
        
        response_data = {
            'success': True,
            'message': 'Task updated successfully',
            'profile': profile.user.username,
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
                    reminder_time_obj = datetime.strptime(reminder_time, '%H:%M').time()
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
                reminder_time_obj = datetime.strptime(reminder_time, '%H:%M').time()
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
        return JsonResponse({'error': f'Task edit failed: {str(e)}'}, status=500)

@require_http_methods(["PATCH"])
def api_task_toggle_complete(request, task_id):
    try:
        task = get_object_or_404(Task, id=task_id, user=request.user)
    except:
        return JsonResponse({
            "error" : "Task by this id is nonexistent"
        })
    profile = request.user.profile
    if not task.isCompleted:
        task.complete_task()
    else:
        task.isCompleted = False
        task.save()
    return JsonResponse({
        'profile': profile.user.username,
        'success': True,
        'isCompleted': task.isCompleted,
    })

@require_http_methods(["GET"])
def api_selected_date_taskView(request):

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    date_str = data.get('date')
    profile = request.user.profile

    try:
        selected_date = datetime.strptime(date_str, '%d-%m-%Y').date()
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
    
    return JsonResponse({
        'profile': profile.user.username,
        'tasks': tasks_data
    })

@require_http_methods(["GET"])
def api_taskView(request, task_id):
    task = get_object_or_404(Task, id=task_id, user=request.user)
    profile = request.user.profile
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
        'profile': profile.user.username,
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