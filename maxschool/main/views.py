from django.shortcuts import render
from accounts.models import CustomUser

def home(request):
    teachers = CustomUser.objects.filter(role='teacher', is_approved=True)
    return render(request, 'main/index.html', {'teachers': teachers})
