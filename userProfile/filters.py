from django.utils import timezone
import django_filters
from .models import Task
from django import forms

class TaskFilter(django_filters.FilterSet):
    dateTime_due__lte = django_filters.DateTimeFilter(
        field_name='dateTime_due',
        lookup_expr='lte',
        widget=forms.DateTimeInput(
            attrs={
                'type': 'dateTime-local',
                'class': 'form-input',
                'min':  timezone.now().strftime('%d-%m-$YT%H:%M'),
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
    