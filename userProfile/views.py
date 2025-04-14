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

## Настройки

@login_required(login_url='users:login')
def settingsView(request):
    if request.method == 'POST' and 'logout' in request.POST:
        logout(request)
        return HttpResponseRedirect(reverse('users:login'))
    return render(request, 'userProfile/settings.html')
    
## Задачи   

class TodoListCreateView(generics.ListCreateAPIView):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    
@login_required(login_url='users:login')
def tasksView(request):
    tasks = Task.objects.filter(user = request.user)
    return render(request, 'userProfile/tasks.html', {'tasks': tasks})

@login_required(login_url='users:login')
def createTask(request):
    if request.method == 'POST':
        form = TaskCreationForm(request.POST, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Задача успешно создана!')
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
        
        d = self.get_date(self.request.GET.get('month', None))
        
        cal = calendar.Calendar()
        month_days = cal.monthdatescalendar(d.year, d.month)
        
        context['calendar'] = month_days
        context['prev_month'] = self.prev_month(d)
        context['next_month'] = self.next_month(d)
        return context

    def get_date(self, req_month):
        if req_month:
            year, month = (int(x) for x in req_month.split('-'))
            return datetime.date(year, month, day=1)
        return datetime.datetime.today()

    def prev_month(self, d):
        first = d.replace(day=1)
        prev_month = first - datetime.timedelta(days=1)
        month = 'month=' + str(prev_month.year) + '-' + str(prev_month.month)
        return month

    def next_month(self, d):
        days_in_month = calendar.monthrange(d.year, d.month)[1]
        last = d.replace(day=days_in_month)
        next_month = last + datetime.timedelta(days=1)
        month = 'month=' + str(next_month.year) + '-' + str(next_month.month)
        return month



