from datetime import *
from django.utils import timezone
from django import forms
from .models import Task

class TaskCreationForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title', 'description', 'priority', 'tag', 'dateTime_due']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-input'}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
            'priority': forms.NumberInput(attrs={'class': 'form-input'}),
            'tag': forms.TextInput(attrs={'class': 'form-input'}),
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
            'tag': 'Тег',
            'dateTime_due': 'Срок выполнения',
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user:
            instance.user = self.user
        if commit:
            instance.save()
        return instance