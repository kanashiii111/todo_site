import json
from django.shortcuts import get_object_or_404
from django.views.generic import ListView
from django.shortcuts import render, HttpResponseRedirect, redirect
from django.http import JsonResponse
from django.urls import reverse
from .models import Task, TaskReminder
from .forms import TaskCreationForm, SUBJECT_CHOICES, TASKTYPE_CHOICES
from django.contrib.auth import logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from .serializers import TaskSerializer
from rest_framework import generics
import calendar
from django.utils.decorators import method_decorator
from .filters import TaskFilter
from datetime import datetime, timedelta, date, timezone
from django.db.models import Q
import requests
from django.views.decorators.csrf import csrf_exempt
from users.forms import ProfileForm
from users.models import Profile
import todo_site.settings
from django.core.management.base import BaseCommand


## Настройки

@login_required(login_url='users:login')
def profileRedirect(request):
    return redirect('userProfile:settings')

@csrf_exempt
def telegram_webhook(request):
    if request.user.profile.telegram_notifications == False: return
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

def send_telegram_message(chat_id, text):
    url = f"https://api.telegram.org/bot{todo_site.settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML'
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()  # Проверка на ошибки HTTP
        return True
    except requests.exceptions.RequestException as e:
        print(f"Ошибка отправки в Telegram: {e}")
        return False

class Command(BaseCommand):
    help = 'Send task reminders to users'

    def handle(self, *args, **options):
        now = timezone.now()
        reminders = TaskReminder.objects.filter(
            is_active=True,
            task__isCompleted=False
        ).select_related('task')

        for reminder in reminders:
            task = reminder.task
            remind_date = task.dateTime_due - timezone.timedelta(days=reminder.remind_before_days)
            
            # Проверяем, нужно ли отправлять напоминание
            if now >= remind_date and (
                reminder.last_reminder_sent is None or 
                reminder.last_reminder_sent < remind_date
            ):
                # Отправляем напоминание
                message = f"⏰ Напоминание: {task.title}\n" \
                     f"📅 Срок: {task.dateTime_due.strftime('%d.%m.%Y %H:%M')}\n" \
                     f"📝 {task.description or '-'}"
            
                if reminder.task.user.profile.telegram_notifications and reminder.task.user.profile.telegram_chat_id:
                    try:
                        send_telegram_message(
                            reminder.task.user.profile.telegram_chat_id,
                            message
                        )
                    except Exception as e:
                        self.stdout.write(f"Ошибка отправки в Telegram: {e}")
                        
                reminder.last_reminder_sent = now
                reminder.save()

                # Если это повторяющееся напоминание, обновляем дату
                if reminder.repeat_interval > 0:
                    new_remind_days = reminder.remind_before_days + reminder.repeat_interval
                    if new_remind_days < (task.dateTime_due - now).days:
                        reminder.remind_before_days = new_remind_days
                        reminder.save()
                    else:
                        reminder.is_active = False
                        reminder.save()

@login_required(login_url='users:login')
def settingsView(request):
    profile = get_object_or_404(Profile, user=request.user)

    if request.method == 'POST':
        if 'logout' in request.POST:
            logout(request)
            return HttpResponseRedirect(reverse('users:login'))
        if 'setTelegramNotis' in request.POST:
            profile.telegram_notifications = not profile.telegram_notifications
            profile.save() 
            return redirect("userProfile:settings")
        if 'save_chat_id' in request.POST:
            new_chat_id = request.POST.get("telegram_chat_id", '').strip()
            if new_chat_id:
                profile.telegram_chat_id = new_chat_id
                profile.save() 
                return redirect("userProfile:settings")
        if 'sendmsg' in request.POST:
            if profile.telegram_notifications != False:
                chat_id = profile.telegram_chat_id
                response_text = "Тест отправки сообщения"
                requests.post(
                    f"https://api.telegram.org/bot{todo_site.settings.TELEGRAM_BOT_TOKEN}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": response_text,
                        "parse_mode": "Markdown"
                    }
                )
            else:
                chat_id = profile.telegram_chat_id
                response_text = "Галочка не нажата"
                requests.post(
                    f"https://api.telegram.org/bot{todo_site.settings.TELEGRAM_BOT_TOKEN}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": response_text,
                        "parse_mode": "Markdown"
                    }
                )
                
    
    form = ProfileForm(instance=profile)
    return render(request, 'userProfile/settings.html', {'profile' : profile, 'form' : form})
    
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
            task.isCompleted = not task.isCompleted
            task.save()
        return redirect('userProfile:tasks')
    
    search_query = request.GET.get('search', '')
    
    # Фильтруем задачи по пользователю и поисковому запросу
    tasks = Task.objects.filter(user=request.user)
    profile = request.user.profile
    
    if search_query:
        tasks = tasks.filter(
            Q(title__icontains=search_query) | 
            Q(description__icontains=search_query))

    task_filter = TaskFilter(request.GET, queryset=Task.objects.filter(user=request.user))
    tasks = task_filter.qs.order_by('dateTime_due')

    today = datetime.now().date()
    days = []
    
    for i in range(7):
        current_date = today + timedelta(days=i)
        if i == 0:
            day_name = "Сегодня"
        elif i == 1:
            day_name = "Завтра"
        else:
            day_name = current_date.strftime("%d.%m.%Y")
        
        days.append({
            'date': current_date,
            'name': day_name,
            'tasks': [task for task in tasks if task.dateTime_due.date() == current_date]
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
    return JsonResponse({
        'title': task.title,
        'description': task.description,
        'subject': task.subject,
        'taskType': task.taskType,
        'dateTime_due': task.dateTime_due.isoformat(),
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
        
        context.update({
            'calendar': month_days,
            'prev_month': self.prev_month(selected_date),
            'next_month': self.next_month(selected_date),
            'current_month': selected_date,
            'today': date.today(),
            'tasks': tasks,
            'month_name': self.get_month_name(selected_date),
            'SUBJECT_CHOICES': SUBJECT_CHOICES,
            'TASKTYPE_CHOICES': TASKTYPE_CHOICES,
            'form' : TaskCreationForm(user = self.request.user),
        })
        return context

    def get_date(self, req_month):
        """Парсит дату из параметра запроса или возвращает текущую дату"""
        if req_month:
            year, month = map(int, req_month.split('-'))
            return date(year, month, day=1)
        return date.today()

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
        


