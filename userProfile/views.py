from django.shortcuts import render

def profile_page_view(request, page_slug):
    valid_pages = ['settings', 'calendar', 'tasks']
    if page_slug not in valid_pages:
        return render(request, 'userProfile/404.html', status=404)
    return render(request, f'userProfile/{page_slug}.html')
    

