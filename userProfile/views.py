## Фронт
import json
from django.db import OperationalError
from django.http import Http404, JsonResponse
from django.views import View
from django.views.decorators.http import require_POST, require_http_methods
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.contrib.auth import authenticate, update_session_auth_hash, logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from django.shortcuts import get_object_or_404
from .models import Task, TaskReminder, Subject, TaskType
import calendar
from django.utils.decorators import method_decorator
from datetime import datetime, time, timedelta, date
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from users.models import Profile
from django.conf import settings
import requests
import logging

logger = logging.getLogger(__name__)

@require_POST
@csrf_exempt
def telegram_webhook(request):
    from django.db import connection, transaction
    import time
    
    max_retries = 3
    retry_delay = 0.5
    
    for attempt in range(max_retries):
        try:
            # Явное управление соединением
            with connection.cursor() as cursor:
                data = json.loads(request.body.decode('utf-8'))
                message = data.get('message', {})
                
                if message.get('text') == '/start':
                    chat_id = message['chat']['id']
                    
                    # Используем транзакцию
                    with transaction.atomic():
                        # Ваша логика обработки
                        response_text = (
                            f"🔑 Ваш Telegram Chat ID: `{chat_id}`\n\n"
                            "1. Скопируйте этот номер\n"
                            "2. Вставьте его в поле 'Telegram Chat ID' на сайте\n"
                            "3. Сохраните изменения\n\n"
                            "Теперь вы будете получать уведомления о задачах!"
                        )
                        
                        requests.post(
                            f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
                            json={
                                "chat_id": chat_id,
                                "text": response_text,
                                "parse_mode": "Markdown"
                            },
                            timeout=3
                        )
                    
                    return JsonResponse({'status': 'ok'})
                
            break  # Успешное выполнение
            
        except OperationalError as e:
            if attempt == max_retries - 1:
                logger.error(f"Database locked after {max_retries} attempts")
                return JsonResponse({'status': 'error'}, status=503)
            time.sleep(retry_delay)
    return JsonResponse({'status': 'ok'})        

# Настройки

@require_http_methods(["GET"])
def api_settingsView(request):
    profile = get_object_or_404(Profile, user=request.user)

    return JsonResponse({
        'profile': {
            'username': request.user.username,
            'status': profile.status,
            'telegram_notifications': profile.telegram_notifications,
            'telegram_chat_id': profile.telegram_chat_id,
            'current_xp': str(profile.xp),
            'xp_for_next_status': str(profile.xp_for_next_status())
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
    old_username = user.username
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    # Обновление никнейма
    if 'username' in data:
        new_username = data['username'].strip()
        if new_username and new_username != user.username:
            if len(new_username) < 3:
                return JsonResponse({'error': 'Username too short (min 3 chars)'}, status=400)
            user.username = new_username
            response_data['username'] = new_username

    # Обновление пароля
    if 'password' in data and 'current_password' in data:
        current_password = data['current_password']
        new_password = data['password']
        
        if not authenticate(username=old_username, password=current_password):
            return JsonResponse({'error': 'Current password is incorrect', 'username' : user.username}, status=400)
        
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

@require_http_methods(["GET"])
def api_tasksView(request):
    profile = request.user.profile

    tasks = Task.objects.filter(user=request.user).order_by('dateTime_due')

    taskList = []
    for task in tasks:
        task_due_local = timezone.localtime(task.dateTime_due)
        taskList.append({
            'id': task.id,
            'title': task.title,
            'description': task.description,
            'priority': task.priority,
            'isCompleted': task.isCompleted,
            'due_date': task_due_local,
            'subject': {
                'id': task.subject.id,
                'name': task.subject.name
            },
            'task_type': {
                'id': task.taskType.id,
                'name': task.taskType.name
            },
        })

    return JsonResponse({
        'profile': profile.user.username, 
        'tasks': taskList,
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
        priority = data.get('priority')
        subject_id = data.get('subject_id')
        task_type_id = data.get('taskType_id')
        date_time_due = data.get('dateTime_due')
        telegram_notifications = data.get('telegram_notifications', False)
        
        if not all([title, priority, subject_id, task_type_id, date_time_due]):
            return JsonResponse({'error': 'Missing required fields: title, subject_id, taskType_id, dateTime_due'}, status=400)
        
        try:
            subject = Subject.objects.get(id=subject_id)
            task_type = TaskType.objects.get(id=task_type_id)
        except (Subject.DoesNotExist, TaskType.DoesNotExist):
            return JsonResponse({'error': 'Invalid subject or task type'}, status=400)

        
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
            priority=priority,
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
                'priority': task.priority,
                'subject': {
                    'id': task.subject.id,
                    'name': task.subject.name
                },
                'task_type': {
                    'id': task.taskType.id,
                    'name': task.taskType.name
                },
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
        new_priority = data.get('priority', task.priority)
        new_subject_id = data.get('subject_id', task.subject.id)
        new_task_type_id = data.get('taskType_id', task.taskType.id)
        new_date_time_due = data.get('dateTime_due', task.dateTime_due)
        telegram_notifications = data.get('telegram_notifications', False)
        
        try:
            new_subject = Subject.objects.get(id=new_subject_id)
            new_task_type = TaskType.objects.get(id=new_task_type_id)
        except (Subject.DoesNotExist, TaskType.DoesNotExist):
            return JsonResponse({'error': 'Invalid subject or task type'}, status=400)

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
        task.priority = new_priority
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
                'priority': task.priority,
                'subject': {
                    'id': task.subject.id,
                    'name': task.subject.name
                },
                'task_type': {
                    'id': task.taskType.id,
                    'name': task.taskType.name
                },
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
        'priority': task.priority,
        'subject': {
            'id': task.subject.id,
            'name': task.subject.name
        },
        'task_type': {
            'id': task.taskType.id,
            'name': task.taskType.name
        },
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

@require_http_methods(["GET"])
def api_tagsView(request):
    profile = request.user.profile
    subjects = Subject.objects.filter(user=request.user)
    taskTypes = TaskType.objects.filter(user=request.user)

    subjects_list = []
    for subject in subjects:
        subjects_list.append({
            "name": subject.name,
            "id": subject.id
        })

    taskTypes_list = []
    for taskType in taskTypes:
        taskTypes_list.append({
            "name": taskType.name,
            "id": taskType.id
        })

    return JsonResponse({
        'profile': profile.user.username, 
        'subjects': subjects_list,
        'taskTypes': taskTypes_list,
    })

@require_http_methods(["GET"])
def api_tagView(request):
    profile = request.user.profile

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    try:
        subject_id = data.get('subject_id')
        taskType_id = data.get('taskType_id')
        
        if not subject_id and not taskType_id:
            return JsonResponse({
                'error': "Missing subject_id/taskType_id"
            })
            
        response_data = {
            'profile' : profile.user.username,
        }
        
        if subject_id:
            subject = get_object_or_404(Subject, id=subject_id, user=request.user)
            response_data['subject'] = {'id': subject.id, 'name': subject.name}
        
        if taskType_id:
            taskType = get_object_or_404(TaskType, id=taskType_id, user=request.user)
            response_data['taskType'] = {'id': taskType.id, 'name': taskType.name}
        
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse({'error': f'Tag view failed: {str(e)}'}, status=500)

@require_http_methods(["POST"])
def api_tagsCreate(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    profile = request.user.profile

    try:
        subject_name = data.get('subject_name')
        taskType_name = data.get('taskType_name')
        
        if not subject_name and not taskType_name:
            return JsonResponse({
                'error': "Missing subject_name/taskType_name"
            })
            
        response_data = {
            'success': True,
            'message': 'Tags created successfully',
            'profile' : profile.user.username,
        }
        
        if subject_name:
            subject = Subject.objects.create(
                user=request.user,
                name=subject_name
            )
            response_data['subject'] = {'id': subject.id, 'name': subject_name}
        
        if taskType_name:
            taskType = TaskType.objects.create(
                user=request.user,
                name=taskType_name
            )
            response_data['taskType'] = {'id': taskType.id, 'name': taskType_name}
        
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse({'error': f'Tag creation failed: {str(e)}'}, status=500)

@require_http_methods(["DELETE"])
def api_tagsDelete(request):
    profile = request.user.profile
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    try:

        response_data = {
            'profile' : profile.user.username,
            'tasks_with_subject': [],
            'tasks_with_taskType': []
        }

        tasks_with_subject= []
        tasks_with_taskType = []
        subject_id = data.get('subject_id')
        taskType_id = data.get('taskType_id')

        if subject_id: 
            subject = get_object_or_404(Subject, id=subject_id, user=request.user)
            tasks_with_subject.extend(list(Task.objects.filter(subject=subject, user=request.user).values_list('title', flat=True)))
        if taskType_id: 
            taskType = get_object_or_404(TaskType, id=taskType_id, user=request.user)
            tasks_with_taskType.extend(list(Task.objects.filter(taskType=taskType, user=request.user).values_list('title', flat=True)))

        if subject_id: 
            if tasks_with_subject: 
                return JsonResponse({
                    "error": f"Subject by this id is being used in tasks {tasks_with_subject}"
                })
            subject.delete() 
            response_data['subject'] = {"success": True, "message": "Subject deleted"}

        if taskType_id:
            if tasks_with_taskType: 
                return JsonResponse({
                    "error": f"TaskType by this id is being used in tasks {tasks_with_taskType}"
                })
            taskType.delete()
            response_data['taskType'] = {"success": True, "message": "TaskType deleted"}

        return JsonResponse(response_data)
    except Http404:
        return JsonResponse({
            'success': False, 
            'message': 'Tag by this id is nonexistent'
        })
    
@require_http_methods(["PUT"])
def api_tagEdit(request):
    profile = request.user.profile
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    try:

        response_data = {
            'profile': profile.user.username,
        }

        subject_id = data.get('subject_id')
        if subject_id:
            subject = get_object_or_404(Subject, id=subject_id, user=request.user)
            new_subject_name = data.get('subject_name', subject.name)
            subject.name = new_subject_name
            subject.save()
            response_data['subject'] = {
                "success": True,
                "message": "Subject edited successfully"   
            }

        taskType_id = data.get('taskType_id')
        if taskType_id: 
            taskType = get_object_or_404(TaskType, id=taskType_id, user=request.user)
            new_taskType_name = data.get('taskType_name', taskType.name)
            taskType.name = new_taskType_name
            taskType.save()
            response_data['taskType'] = {
                "success": True,
                "message": "TaskType edited successfully"   
            }

        return JsonResponse(response_data)
    except Exception as e:
        return JsonResponse({'error': f'Tag edit failed: {str(e)}'}, status=500)