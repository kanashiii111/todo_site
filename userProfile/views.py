from collections import defaultdict
import datetime
from django.views.generic import ListView
from django.shortcuts import render, HttpResponseRedirect, redirect
from django.urls import reverse
from .models import Task, Event
from .forms import TaskCreationForm
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from .serializers import TaskSerializer
from rest_framework import generics
import calendar
from django.utils.decorators import method_decorator
from .filters import TaskFilter

## Настройки

@login_required(login_url='users:login')
def settingsView(request):
    if request.method == 'POST' and 'logout' in request.POST:
        logout(request)
        return HttpResponseRedirect(reverse('users:login'))
    return render(request, 'userProfile/settings.html')
    
## Задачи   

class TaskListCreateView(generics.ListCreateAPIView):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    
@login_required(login_url='users:login')
def tasksView(request):
    tasks = Task.objects.filter(user = request.user)
    task_filter = TaskFilter(request.GET, queryset=tasks) 
    return render(request, 'userProfile/tasks.html', {'tasks': tasks, 'filter': task_filter}, )

@login_required(login_url='users:login')
def createTask(request):
    if request.method == 'POST':
        form = TaskCreationForm(request.POST, user=request.user)
        if form.is_valid():
            form.save()
            return redirect('tasks')
    else:
        form = TaskCreationForm(user=request.user)
    return render(request, 'userProfile/create_task.html', {'form': form})

## Календарь

@method_decorator(login_required(login_url='users:login'), name='dispatch')
class CalendarView(ListView):
    model = Event
    template_name = 'userProfile/calendar.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Получаем выбранную дату (из параметра или текущую)
        selected_date = self.get_date(self.request.GET.get('month', None))
        
        # Создаем календарь и получаем матрицу дней
        cal = calendar.Calendar()
        month_days = cal.monthdatescalendar(selected_date.year, selected_date.month)
        
        # Оптимизированный запрос для событий (текущий месяц + соседние дни)
        events = Event.objects.filter(
            user=self.request.user,
            start_time__year=selected_date.year,
            start_time__month=selected_date.month
        ).select_related('user').order_by('start_time')
        
        # Создаем словарь событий для быстрого доступа по дате
        events_dict = defaultdict(list)
        for event in events:
            events_dict[event.start_time.date()].append(event)
        
        # Заполняем контекст
        context.update({
            'calendar': month_days,
            'prev_month': self.prev_month(selected_date),
            'next_month': self.next_month(selected_date),
            'current_month': selected_date,  # Объект date выбранного месяца
            'today': datetime.date.today(),
            'events_dict': events_dict,
            'month_name': self.get_month_name(selected_date),
        })
        return context

    def get_date(self, req_month):
        """Парсит дату из параметра запроса или возвращает текущую дату"""
        if req_month:
            year, month = map(int, req_month.split('-'))
            return datetime.date(year, month, day=1)
        return datetime.date.today()

    def prev_month(self, d):
        """Генерирует URL параметр для предыдущего месяца"""
        first = d.replace(day=1)
        prev_month = first - datetime.timedelta(days=1)
        return f'month={prev_month.year}-{prev_month.month}'

    def next_month(self, d):
        """Генерирует URL параметр для следующего месяца"""
        days_in_month = calendar.monthrange(d.year, d.month)[1]
        last = d.replace(day=days_in_month)
        next_month = last + datetime.timedelta(days=1)
        return f'month={next_month.year}-{next_month.month}'

    def get_month_name(self, date_obj):
        """Возвращает локализованное название месяца"""
        month_names = [
            'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
            'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
        ]
        return month_names[date_obj.month - 1]
        


