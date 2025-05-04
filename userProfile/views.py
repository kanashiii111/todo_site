import json
from django.shortcuts import get_object_or_404
from django.views.generic import ListView
from django.shortcuts import render, HttpResponseRedirect, redirect
from django.http import JsonResponse
from django.urls import reverse
from .models import Task, TaskReminder
from .forms import TaskCreationForm, SUBJECT_CHOICES, TASKTYPE_CHOICES
from django.contrib.auth import logout, update_session_auth_hash
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from .serializers import TaskSerializer
from rest_framework import generics
import calendar
from django.utils.decorators import method_decorator
from .filters import TaskFilter
from datetime import datetime, time, timedelta, date
from django.utils import timezone
from django.db.models import Q
import requests
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from users.forms import CustomPasswordChangeForm, EmailChangeForm, ProfileForm
from users.models import Profile
import todo_site.settings
from django.core.management.base import BaseCommand
from django.contrib import messages
from .tasks import send_reminder

## Настройки

@login_required(login_url='users:login')
def profileRedirect(request):
    return redirect('userProfile:settings')

@require_POST   
@csrf_exempt
def telegram_webhook(request):
    if request.method == "POST":
        data = json.loads(request.body)
        #send_reminder.delay(data)
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

@login_required(login_url='users:login')
def settingsView(request):
    profile = get_object_or_404(Profile, user=request.user)
    password_form = CustomPasswordChangeForm(request.user)
    email_form = EmailChangeForm(request.user)

    if request.method == 'POST':
        if 'logout' in request.POST:
            logout(request)
            return HttpResponseRedirect(reverse('users:login'))
        elif 'setTelegramNotis' in request.POST:
            profile.telegram_notifications = not profile.telegram_notifications
            profile.save() 
            return redirect("userProfile:settings")
        elif 'save_chat_id' in request.POST:
            new_chat_id = request.POST.get("telegram_chat_id", '').strip()
            if new_chat_id:
                profile.telegram_chat_id = new_chat_id
                profile.save() 
                return redirect("userProfile:settings")
        elif 'edit_profile' in request.POST:
            new_username = request.POST.get('username', '').strip()
            new_status = request.POST.get('status', '').strip()
            if new_username:
                request.user.username = new_username
                request.user.save()
            profile.status = new_status
            if 'avatar' in request.FILES:
                profile.avatar = request.FILES['avatar']
            profile.save()
        elif 'change_password' in request.POST:
            password_form = CustomPasswordChangeForm(request.user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Пароль успешно изменен!')
                return redirect("userProfile:settings")
            else:
                for error in password_form.errors.values():
                    messages.error(request, error)
                    
        elif 'change_email' in request.POST:
            email_form = EmailChangeForm(request.user, request.POST)
            if email_form.is_valid():
                new_email = email_form.cleaned_data['new_email']
                request.user.email = new_email
                request.user.save()
                profile.email = new_email
                profile.email_verified = False
                profile.save()
                # Здесь можно добавить отправку письма для подтверждения
                messages.success(request, 'Email успешно изменен!')
                return redirect("userProfile:settings")
            
        return redirect("userProfile:settings")
    form = ProfileForm(instance=profile)
    context = {
        'profile': profile,
        'password_form': password_form,
        'email_form': email_form,
        'profile' : profile,
        'form' : form,
    }
    return render(request, 'userProfile/settings.html', context)
    
## Задачи   

class TaskListCreateView(generics.ListCreateAPIView):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    
@login_required(login_url='users:login')
def tasksView(request):
    if request.method == 'POST':
        if 'deleteTask' in request.POST:
            task_id = request.POST.get('deleteTask')
            task = get_object_or_404(Task, id=task_id, user=request.user)
            task.delete()
            return redirect('userProfile:tasks')
        elif 'completeTask' in request.POST:
            task_id = request.POST.get('completeTask')
            task = get_object_or_404(Task, id=task_id, user=request.user)
            if not task.isCompleted:
                task.complete_task()
            else:
                task.isCompleted = False
                task.save()
        return redirect('userProfile:tasks')
    
    search_query = request.GET.get('search', '')
    
    tasks = Task.objects.filter(user=request.user)
    profile = request.user.profile
    
    if search_query:
        tasks = tasks.filter(
            Q(title__icontains=search_query) | 
            Q(description__icontains=search_query))

    task_filter = TaskFilter(request.GET, queryset=Task.objects.filter(user=request.user))
    tasks = task_filter.qs.order_by('dateTime_due')

    now = timezone.now()
    today = now.date()
    days = []
    
    for i in range(7):
        current_date = today + timedelta(days=i)
        if i == 0:
            day_name = "Сегодня"
        elif i == 1:
            day_name = "Завтра"
        else:
            day_name = current_date.strftime("%d.%m.%Y")
            
        start_of_day = datetime.combine(current_date, time.min, tzinfo=timezone.get_current_timezone())
        end_of_day = datetime.combine(current_date, time.max, tzinfo=timezone.get_current_timezone())
        
        day_tasks = []
        for task in tasks:
            task_due_local = timezone.localtime(task.dateTime_due)
            if start_of_day <= task_due_local <= end_of_day:
                day_tasks.append(task)
        
        days.append({
            'date': current_date,
            'name': day_name,
            'tasks': [task for task in tasks if start_of_day <= task.dateTime_due <= end_of_day]
        })
    context = {
        'days': days,
        'SUBJECT_CHOICES': SUBJECT_CHOICES,
        'TASKTYPE_CHOICES': TASKTYPE_CHOICES,
        'form' : TaskCreationForm(user = request.user),
        'filter' : task_filter,
        'search_query' : search_query,
        'profile' : profile,
    }

    return render(request, 'userProfile/tasks.html', context)

@login_required(login_url='users:login')
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
    

@login_required(login_url='users:login')
def deleteTask(request, task_id):
    if request.method == 'POST':
        task = get_object_or_404(Task, id=task_id, user=request.user)
        task.delete()
    return redirect(request.POST.get('next', 'userProfile:tasks'))

@login_required(login_url='users:login')
def createTask(request):
    if request.method == 'POST':
        form = TaskCreationForm(request.POST, user=request.user)
        if form.is_valid():
            form.save()
            return redirect('userProfile:tasks')
    else:
        form = TaskCreationForm(user=request.user)
    return render(request, 'userProfile/create_task.html', {'form': form})

@login_required(login_url='users:login')
def editTask(request, task_id):
    task = get_object_or_404(Task, id=task_id, user=request.user)

    if request.method == 'POST':
        form = TaskCreationForm(request.POST, instance=task, user=request.user)
        if form.is_valid():
            form.save()
            return redirect('userProfile:tasks')
    else:
        # Заполняем форму данными задачи
        form = TaskCreationForm(instance=task, user=request.user)
    
    return render(request, 'userProfile/task_edit.html', {
        'form': form,
        'task': task
    })

@login_required(login_url='users:login')
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

@method_decorator(login_required(login_url='users:login'), name='dispatch')
class CalendarView(ListView):
    model = Task
    template_name = 'userProfile/calendar.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        selected_date = self.get_date(self.request.GET.get('month', None))
        
        cal = calendar.Calendar()
        month_days = cal.monthdatescalendar(selected_date.year, selected_date.month)
        
        tasks = Task.objects.filter(
            user=self.request.user,
        ).select_related('user').order_by('dateTime_due')
        
        tasks_list = []
        for task in tasks:
            local_due = timezone.localtime(task.dateTime_due)
            tasks_list.append({
                'id': task.id,
                'title': task.title,
                'description': task.description,
                'subject': task.subject,
                'taskType': task.taskType,
                'dateTime_due': task.dateTime_due,
                'local_date': local_due.date(),
                'reminder': task.reminder if hasattr(task, 'reminder') else None
            })
        
        profile = get_object_or_404(Profile, user=self.request.user)
        today = timezone.localtime(timezone.now()).date()
        context.update({
            'calendar': month_days,
            'prev_month': self.prev_month(selected_date),
            'next_month': self.next_month(selected_date),
            'current_month': selected_date,
            'today': today,
            'tasks': tasks_list,
            'month_name': self.get_month_name(selected_date),
            'SUBJECT_CHOICES': SUBJECT_CHOICES,
            'TASKTYPE_CHOICES': TASKTYPE_CHOICES,
            'form' : TaskCreationForm(user = self.request.user),
            'profile' : profile,
        })
        return context

    def get_date(self, req_month):
        """Парсит дату из параметра запроса или возвращает текущую дату"""
        if req_month:
            year, month = map(int, req_month.split('-'))
            return date(year, month, day=1)
        return timezone.localtime(timezone.now()).date()

    def prev_month(self, d):
        """Генерирует URL параметр для предыдущего месяца"""
        first = d.replace(day=1)
        prev_month = first - timedelta(days=1)
        return f'month={prev_month.year}-{prev_month.month}'

    def next_month(self, d):
        """Генерирует URL параметр для следующего месяца"""
        days_in_month = calendar.monthrange(d.year, d.month)[1]
        last = d.replace(day=days_in_month)
        next_month = last + timedelta(days=1)
        return f'month={next_month.year}-{next_month.month}'

    def get_month_name(self, date_obj):
        """Возвращает локализованное название месяца"""
        month_names = [
            'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
            'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
        ]
        return month_names[date_obj.month - 1]