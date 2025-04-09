from django.shortcuts import render, HttpResponseRedirect, redirect
from django.urls import reverse
from .models import Task
from .forms import TaskCreationForm
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from .serializers import TaskSerializer
from rest_framework import generics

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

@login_required(login_url='users:login')
def calendarView(request):
    return render(request, 'userProfile/calendar.html')


