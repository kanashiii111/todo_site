import json

from django.contrib.auth import authenticate, login, logout, get_user_model
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

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
def api_register(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    username = data.get('username')
    password = data.get('password')
    email = data.get('email')
    
    if not username or not password:
        return JsonResponse(
            {'error': 'Username, password and email are required'}, 
            status=400
        )

    User = get_user_model()
    
    if User.objects.filter(username=username).exists():
        return JsonResponse(
            {'error': 'Username already exists'},
            status=400
        )

    try:
        user = User.objects.create_user(
            username=username,
            password=password,
            email=email
        )

        user.save()
        
        return JsonResponse({
            'success': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email
            }
        })
    
    except Exception as e:
        return JsonResponse(
            {'error': f'User creation failed: {str(e)}'},
            status=500
        )

# logout перенес в userProfile/views.py

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