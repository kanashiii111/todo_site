import json

from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.shortcuts import HttpResponseRedirect, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from .forms import LoginUserForm, RegisterForm


def home_redirect(request):
    return redirect('users:login')


def loginUser(request):
    if request.method == 'POST':
        if 'login' in request.POST:
            form = LoginUserForm(request.POST)
            if form.is_valid():
                cd = form.cleaned_data
                user = authenticate(
                    request, username=cd['username'], password=cd['password'])
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


@ensure_csrf_cookie
def login_view_placeholder(request):
    return JsonResponse({"detail": "CSRF cookie set"})


@require_POST
def api_login(request):
    try:
        data = json.loads(request.body)
        username = data.get('username')
        password = data.get('password')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    if not username or not password:
        return JsonResponse({'error': 'Username and password required'}, status=400)

    user = authenticate(request, username=username, password=password)

    if user is not None and user.is_active:
        login(request, user)
        return JsonResponse({
            'success': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email
            }
        })
    else:
        return JsonResponse({'error': 'Invalid credentials'}, status=401)


@require_POST
def api_logout(request):
    logout(request)
    return JsonResponse({'success': True, 'message': 'Logged out successfully'})


@require_GET
def check_auth_status(request):
    if request.user.is_authenticated:
        profile = getattr(request.user, 'profile', None)
        return JsonResponse({
            'isAuthenticated': True,
            'user': {
                'id': request.user.id,
                'username': request.user.username,
                'email': request.user.email,
            }
        })
    else:
        return JsonResponse({'isAuthenticated': False}, status=401)
