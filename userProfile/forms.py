from django import forms
from .models import Task

class TaskCreationForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title', 'description', 'priority', 'tag']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-input'}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),  # Textarea для описания
            'priority': forms.NumberInput(attrs={'class': 'form-input'}),
            'tag': forms.TextInput(attrs={'class': 'form-input'}),
        }
        labels = {
            'title': 'Название',
            'description': 'Описание',
            'priority': 'Приоритетность',
            'tag': 'Тег',
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