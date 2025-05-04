from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from django.contrib.auth.models import User
from .models import Profile

class LoginUserForm(forms.Form):
    username = forms.CharField(label='Логин', widget=forms.TextInput(attrs={'class': 'form-input'}))
    password = forms.CharField(label='Пароль', widget=forms.PasswordInput(attrs={'class': 'form-input'}))
    
class RegisterForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        label='Почта',
    )
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
        fields = ['username', 'email', 'password1', 'password2']

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
    class Meta:
        model = Profile
        fields = ['avatar', 'status']

        
class EmailChangeForm(forms.Form):
    new_email = forms.EmailField(
        label="Новый email",
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'Введите новый email'
        }),
    )
    current_password = forms.CharField(
        label="Текущий пароль",
        widget=forms.PasswordInput(
            attrs={'class': 'form-input',
            'placeholder': 'Введите текущий пароль'
        }),
        required=True,
        help_text='Требуется для подтверждения изменений.'
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_current_password(self):
        password = self.cleaned_data.get('current_password')
        if not self.user.check_password(password):
            raise forms.ValidationError("Неверный пароль")
        return password

class CustomPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['old_password'].widget.attrs.update({
            'class': 'form-input',
            'placeholder': 'Текущий пароль'
        })
        self.fields['new_password1'].widget.attrs.update({
            'class': 'form-input',
            'placeholder': 'Новый пароль'
        })
        self.fields['new_password2'].widget.attrs.update({
            'class': 'form-input',
            'placeholder': 'Повторите новый пароль'
        })
        self.fields['new_password1'].help_text = """
        <ul class="password-help">
            <li>Минимум 8 символов</li>
            <li>Не должен быть слишком простым</li>
            <li>Рекомендуется использовать буквы, цифры и спецсимволы</li>
        </ul>
        """