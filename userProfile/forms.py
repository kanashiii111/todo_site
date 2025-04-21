from datetime import *
from django.utils import timezone
from django import forms
from .models import Task

SUBJECT_CHOICES = {
    "Программирование" : "Программирование",
    "Информатика": "Информатика",
    "Дискретная математика": "Дискретная математика",
}

TASKTYPE_CHOICES = {
    "Лабораторная работа" : "Лабораторная работа",
    "Практическая работа" : "Практическая работа", 
    "Домашняя работа" : "Домашняя работа", 
    "Экзамен" : "Экзамен",
}

class TaskCreationForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title', 'description', 'priority', 'subject', 'taskType', 'dateTime_due']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-input'}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
            'priority': forms.NumberInput(attrs={'class': 'form-input'}),
            'subject': forms.Select(
                attrs={'class' : 'form-input'},
                choices=SUBJECT_CHOICES,
            ),
            'taskType': forms.Select(
                attrs={'class' : 'form-input'},
                choices=TASKTYPE_CHOICES,
            ),
            'dateTime_due': forms.DateTimeInput(attrs={
                    'class': 'form-input',
                    'type': 'datetime-local',
                    'min': str(timezone.now().date()),
                }),
        }
        labels = {
            'title': 'Название',
            'description': 'Описание',
            'priority': 'Приоритетность',
            'subject' : 'Предмет',
            'taskType' : 'Задача',
            'dateTime_due': 'Срок выполнения',
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        instance = kwargs.get('instance', None)
        super().__init__(*args, **kwargs)
        
        self.fields['subject'].widget.choices = [(k, v) for k, v in SUBJECT_CHOICES.items()]
        self.fields['taskType'].widget.choices = [(k, v) for k, v in TASKTYPE_CHOICES.items()]
        
        # Если есть instance (редактирование), устанавливаем начальные значения
        if instance:
            self.fields['dateTime_due'].widget.attrs['min'] = str(timezone.now().date())
            if instance.dateTime_due:
                dt_value = instance.dateTime_due.strftime('%Y-%m-%dT%H:%M')
                self.initial['dateTime_due'] = dt_value
        
    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user:
            instance.user = self.user
        if commit:
            instance.save()
        return instance