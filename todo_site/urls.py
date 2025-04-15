from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from userProfile.views import TaskListCreateView

urlpatterns = [
    path('api/tasks/', TaskListCreateView.as_view(), name='tasks_list'),
    path('admin/', admin.site.urls),
    path('', include('users.urls', namespace='users')),
    path('', include('userProfile.urls',))
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
