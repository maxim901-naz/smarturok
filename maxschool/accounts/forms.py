from django import forms
from django.contrib.auth.forms import UserCreationForm,UserChangeForm
from .models import CustomUser
from .models import Subject

class CustomUserCreationForm(UserCreationForm):
    field_order = ['username', 'email', 'password1', 'password2', 'desired_subject', 'captcha_answer']

    captcha_answer = forms.IntegerField(
        label='РџСЂРѕРІРµСЂРєР°',
        min_value=0,
        widget=forms.NumberInput(attrs={'autocomplete': 'off', 'inputmode': 'numeric'})
    )

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password1', 'password2', 'desired_subject']

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip().lower()
        if not email:
            raise forms.ValidationError('РЈРєР°Р¶РёС‚Рµ email.')
        if CustomUser.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('РџРѕР»СЊР·РѕРІР°С‚РµР»СЊ СЃ С‚Р°РєРёРј email СѓР¶Рµ СЃСѓС‰РµСЃС‚РІСѓРµС‚.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'student'  # Р°РІС‚РѕРјР°С‚РёС‡РµСЃРєРё Р·Р°РґР°С‘Рј СЂРѕР»СЊ
        user.is_approved = True
        if commit:
            user.save()
        return user
from django.contrib.auth.forms import UserCreationForm, UserChangeForm


class AdminUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = [
            "username",
            "email",
            "password1",
            "password2",
            "first_name",
            "last_name",
            "role",
            "desired_subject",
            "subjects_taught",
            "is_approved",
            "is_email_verified",
            "photo",
            "experience_years",
            "students_count",
            "success_rate",
            "rating",
            "reviews_count",
            "bio",
            "education",
            "methodology",
            "achievements",
            "teacher_payout_percent",
            "teacher_payout_fixed",
            "is_active",
            "is_staff",
            "is_superuser",
        ]


class AdminUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = [
            "username",
            "password",
            "email",
            "first_name",
            "last_name",
            "role",
            "desired_subject",
            "subjects_taught",
            "is_approved",
            "is_email_verified",
            "photo",
            "experience_years",
            "students_count",
            "success_rate",
            "rating",
            "reviews_count",
            "bio",
            "education",
            "methodology",
            "achievements",
            "teacher_payout_percent",
            "teacher_payout_fixed",
            "teachers",
            "is_active",
            "is_staff",
            "is_superuser",
            "groups",
            "user_permissions",
        ]


class TrialLessonForm(forms.Form):
    name = forms.CharField(label="РРјСЏ", max_length=100)
    email = forms.EmailField(label="Email")
    phone = forms.CharField(label="РўРµР»РµС„РѕРЅ", max_length=20)
    subject = forms.ModelChoiceField(queryset=Subject.objects.all(), label='РџСЂРµРґРјРµС‚')
    preferred_time = forms.CharField(label="РЈРґРѕР±РЅРѕРµ РІСЂРµРјСЏ", max_length=100, required=False)
    message = forms.CharField(label="РљРѕРјРјРµРЅС‚Р°СЂРёР№", widget=forms.Textarea, required=False)

from .models import TeacherApplication, Vacancy

class TeacherApplicationForm(forms.ModelForm):
    class Meta:
        model = TeacherApplication
        fields = [
            'vacancy',
            'first_name',
            'last_name',
            'email',
            'phone',
            'years_experience',
            'experience',
            'motivation',
        ]
        widgets = {
            'experience': forms.Textarea(attrs={'rows': 4}),
            'motivation': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['vacancy'].queryset = Vacancy.objects.filter(is_active=True).order_by('order', 'title')
        self.fields['vacancy'].required = True

        base_class = 'w-full rounded-xl border border-slate-300 px-4 py-3 focus:border-secondary focus:ring-2 focus:ring-secondary/30'
        textarea_class = base_class + ' min-h-[120px]'

        self.fields['vacancy'].empty_label = 'Выберите вакансию'
        self.fields['vacancy'].widget.attrs.update({'class': base_class})
        self.fields['first_name'].widget.attrs.update({'class': base_class, 'placeholder': 'Имя'})
        self.fields['last_name'].widget.attrs.update({'class': base_class, 'placeholder': 'Фамилия'})
        self.fields['email'].widget.attrs.update({'class': base_class, 'placeholder': 'Email'})
        self.fields['phone'].widget.attrs.update({'class': base_class, 'placeholder': '+7 (___) ___-__-__'})
        self.fields['years_experience'].widget.attrs.update({'class': base_class, 'min': 0, 'placeholder': 'Сколько лет'})
        self.fields['experience'].widget.attrs.update({'class': textarea_class, 'placeholder': 'Расскажите об опыте преподавания'})
        self.fields['motivation'].widget.attrs.update({'class': textarea_class, 'placeholder': 'Почему хотите работать с нами?'})

    def clean_vacancy(self):
        vacancy = self.cleaned_data.get('vacancy')
        if vacancy and not vacancy.is_active:
            raise forms.ValidationError('Выбранная вакансия уже неактивна.')
        return vacancy

    def save(self, commit=True):
        application = super().save(commit=False)
        first_name = (application.first_name or '').strip()
        last_name = (application.last_name or '').strip()
        application.name = f'{first_name} {last_name}'.strip()
        if application.vacancy_id:
            application.specialization = application.vacancy.title[:100]
        if not application.specialization:
            application.specialization = 'Заявка преподавателя'
        if commit:
            application.save()
        return application

from accounts.models import Lesson

class LessonFeedbackForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ['topic', 'homework','homework_file', 'teacher_notes']

from lessons.models import Lesson




from .models import BalanceTopUpRequest, StudentVacation

class BalanceTopUpRequestForm(forms.ModelForm):
    class Meta:
        model = BalanceTopUpRequest
        fields = ['package', 'comment']
        widgets = {
            'comment': forms.Textarea(attrs={'rows': 3, 'placeholder': 'РљРѕРјРјРµРЅС‚Р°СЂРёР№ (РЅРµРѕР±СЏР·Р°С‚РµР»СЊРЅРѕ)'}),
        }

class StudentVacationRequestForm(forms.ModelForm):
    class Meta:
        model = StudentVacation
        fields = ['start_date', 'end_date', 'comment']
        widgets = {
            'start_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full rounded-lg border-slate-300 focus:border-secondary focus:ring-secondary',
            }),
            'end_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full rounded-lg border-slate-300 focus:border-secondary focus:ring-secondary',
            }),
            'comment': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Например: поездка с семьёй',
                'class': 'w-full rounded-lg border-slate-300 focus:border-secondary focus:ring-secondary',
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        if start_date and end_date and end_date < start_date:
            self.add_error('end_date', 'Дата окончания не может быть раньше даты начала.')
        return cleaned_data
