from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Profile

class LoginUserForm(forms.Form):
    username = forms.CharField(label='Логин', widget=forms.TextInput(attrs={'class': 'form-input'}))
    password = forms.CharField(label='Пароль', widget=forms.PasswordInput(attrs={'class': 'form-input'}))
    
class RegisterForm(UserCreationForm):
    avatar = forms.ImageField(required=False, label='Аватар')
    username = forms.CharField(label='Логин', help_text='Обязательное поле. Не более 150 символов. Только буквы, цифры и @/./+/-/_.')
    password1 = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={'class': 'form-input'}),
        help_text='<ul>'
                 '<li>Ваш пароль не должен быть слишком похож на другую личную информацию.</li>'
                 '<li>Ваш пароль должен содержать как минимум 8 символов.</li>'
                 '<li>Ваш пароль не может быть одним из широко распространённых паролей.</li>'
                 '<li>Ваш пароль не может состоять только из цифр.</li>'
                 '</ul>'
    )
    password2 = forms.CharField(
        label='Подтверждение пароля',
        widget=forms.PasswordInput(attrs={'class': 'form-input'}),
        help_text='Введите тот же пароль, что и выше, для подтверждения.'
    )

    error_messages = {
        'password_mismatch': 'Пароли не совпадают.',
    }

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
    
class ProfileForm(forms.ModelForm):
    telegram_chat_id = forms.CharField(
        label="Telegram Chat ID",
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Введите ваш Chat ID"}))
    
    class Meta:
        model = Profile
        fields = ['avatar', 'status', 'telegram_notifications']