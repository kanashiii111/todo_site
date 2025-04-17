from django.shortcuts import render, HttpResponseRedirect, redirect
from django.urls import reverse
from django.contrib.auth import authenticate, login, logout
from .forms import LoginUserForm, RegisterForm

def home_redirect(request):
    return redirect('users:login')

def loginUser(request):
    if request.method == 'POST':
        if 'login' in request.POST:
            form = LoginUserForm(request.POST)
            if form.is_valid():
                cd = form.cleaned_data
                user = authenticate(request, username=cd['username'], password=cd['password'])
                if user and user.is_active:
                    login(request, user)
                    return HttpResponseRedirect(reverse('userProfile:tasks'))
        elif 'signUp' in request.POST:
            return redirect('users:register')
    else:
        form = LoginUserForm()
    
    return render(request, 'users/login.html', {'form': form})

def registerUser(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('users:login')
    else:
        form = RegisterForm()
    
    return render(request, 'users/register.html', {'form': form})