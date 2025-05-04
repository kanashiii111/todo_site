from datetime import *
from django.utils import timezone
from django import forms

from users.models import Profile
from .models import Task, TaskReminder

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
    remind_before_days = forms.IntegerField(
        label="Напомнить за (дней)",
        initial=1,
        min_value=1,
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-input'})
    )
    repeat_reminder = forms.IntegerField(
        label="Повторять напоминание каждые (дней)",
        initial=0,
        min_value=0,
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-input'}),
        help_text="0 - не повторять"
    )
    reminder_time = forms.TimeField(
        label="Время напоминания",
        initial='09:00',
        required=False,
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-input'})
    )
    
    class Meta:
        model = Task
        fields = ['title', 'description', 'subject', 'taskType', 'dateTime_due']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-input'}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
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
            'subject' : 'Предмет',
            'taskType' : 'Задача',
            'dateTime_due': 'Срок выполнения',
        }
    
    def clean_dateTime_due(self):
        dateTime_due = self.cleaned_data.get('dateTime_due')
        if dateTime_due:
            if timezone.is_naive(dateTime_due):
                dateTime_due = timezone.make_aware(dateTime_due, timezone.get_current_timezone())
        return dateTime_due

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
        
        from users.models import Profile
        profile = Profile.objects.get(user=self.user)
        
        if profile.telegram_notifications:
            remind_before = self.cleaned_data.get('remind_before_days')
            repeat_interval = self.cleaned_data.get('repeat_reminder', 0)
            reminder_time = self.cleaned_data.get('reminder_time')
            
            if remind_before is not None and remind_before > 0:
                TaskReminder.objects.update_or_create(
                    task=instance,
                    defaults={
                        'remind_before_days': remind_before,
                        'repeat_interval': repeat_interval,
                        'reminder_time': reminder_time,
                        'is_active': True
                    }
                )
            elif hasattr(instance, 'reminder'):
                # Удаляем напоминание, если оно было отключено
                instance.reminder.delete()
        else:
            # Удаляем существующее напоминание, если уведомления отключены
            if hasattr(instance, 'reminder'):
                instance.reminder.delete()
        return instance