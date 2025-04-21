from django.utils import timezone
import django_filters
from .models import Task
from .forms import SUBJECT_CHOICES, TASKTYPE_CHOICES
from django import forms

class TaskFilter(django_filters.FilterSet):
    taskType__exact = django_filters.ChoiceFilter(
        choices=TASKTYPE_CHOICES,
        field_name='taskType',
        lookup_expr='exact',
        label='Задача'
    )

    subject__exact = django_filters.ChoiceFilter(
        choices=SUBJECT_CHOICES,
        field_name = 'subject',
        lookup_expr= 'exact',
        label = 'Предмет',
    )
    