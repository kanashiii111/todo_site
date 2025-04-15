from django.utils import timezone
import django_filters
from .models import Task
from django import forms

class TaskFilter(django_filters.FilterSet):
    
    date_due__lte = django_filters.DateFilter(
        field_name='date_due',
        lookup_expr='lte',
        widget=forms.DateInput(
            attrs={
                'type': 'date',
                'class': 'form-input',
                'min': str(timezone.now().date())
            }
        ),
        label = 'Срок выполнения до'
    )
    
    priority__gte = django_filters.NumberFilter(
        field_name = 'priority',
        lookup_expr= 'gte',
        label = 'Приоритет'
    )
    
    tag__exact = django_filters.CharFilter(
        field_name = 'tag',
        lookup_expr= 'exact',
        label = 'Тег',
    )
    