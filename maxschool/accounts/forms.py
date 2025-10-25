from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser
from .models import Subject

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password1', 'password2', 'desired_subject']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'student'  # автоматически задаём роль
        user.is_approved = True
        if commit:
            user.save()
        return user
from django import forms

class TrialLessonForm(forms.Form):
    name = forms.CharField(label="Имя", max_length=100)
    email = forms.EmailField(label="Email")
    phone = forms.CharField(label="Телефон", max_length=20)
    subject = forms.ModelChoiceField(queryset=Subject.objects.all(), label='Предмет')
    preferred_time = forms.CharField(label="Удобное время", max_length=100, required=False)
    message = forms.CharField(label="Комментарий", widget=forms.Textarea, required=False)

from django import forms
from .models import TeacherApplication

class TeacherApplicationForm(forms.ModelForm):
    class Meta:
        model = TeacherApplication
        fields = ['name', 'email', 'phone', 'specialization', 'experience', 'motivation']
        widgets = {
            'experience': forms.Textarea(attrs={'rows': 3}),
            'motivation': forms.Textarea(attrs={'rows': 3}),
        }

from django import forms
from accounts.models import Lesson

class LessonFeedbackForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ['topic', 'homework','homework_file', 'teacher_notes']

from django import forms
from lessons.models import Lesson


