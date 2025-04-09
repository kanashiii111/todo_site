from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Profile

class LoginUserForm(forms.Form):
    username = forms.CharField(label='Логин', widget=forms.TextInput(attrs={'class': 'form-input'}))
    password = forms.CharField(label='Пароль', widget=forms.PasswordInput(attrs={'class': 'form-input'}))
    
class RegisterForm(UserCreationForm):
    avatar = forms.ImageField(required=False, label='Аватар')

    class Meta:
        model = User
        fields = ['username', 'password1', 'password2', 'avatar']

    def save(self, commit=True):
        user = super().save(commit=True)
        avatar = self.cleaned_data.get('avatar')
        if not hasattr(user, 'profile'):
            profile = Profile.objects.create(user=user)
        else:
            profile = user.profile
        
        if avatar:
            profile.avatar = avatar
            profile.save()
        
        return user
    
