from django.shortcuts import render, HttpResponse
from .models import Task

def settingsView(request):
    return render(request, 'userProfile/settings.html')
    
def tasksView(request):
    tasks = Task.objects.all()
    return render(request, 'userProfile/tasks.html', {'tasks': tasks})

def calendarView(request):
    return render(request, 'userProfile/calendar.html')