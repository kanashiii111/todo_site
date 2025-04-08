from django.shortcuts import render, HttpResponseRedirect
from django.urls import reverse
from django.contrib.auth import authenticate, login, logout
from .forms import LoginUserForm

def loginUser(request):
    if request.method == 'POST':
        form = LoginUserForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            user = authenticate(request, username=cd['username'], password=cd['password'])
            if user and user.is_active:
                login(request, user)
                return HttpResponseRedirect(reverse('profile_page', kwargs={'page_slug': 'tasks'}))
    else:
        form = LoginUserForm()
    return render(request, 'users/login.html', {'form': form})

def logoutUser(request):
    logout(request)
    return HttpResponseRedirect(reverse('users:login'))
