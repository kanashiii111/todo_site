from django.test import TestCase
from django.utils import timezone
from .forms import TaskCreationForm

class FormDateTest(TestCase):
    def test_date_input(self):
        test_data = {'date_due': '15-12-2023'}
        form = TaskCreationForm(data=test_data)
        print("Form is valid:", form.is_valid())
        if form.is_valid():
            print("Cleaned data:", form.cleaned_data['date_due'])
