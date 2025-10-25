from django import forms
from .models import LessonBooking
from accounts.models import CustomUser

# class LessonBookingForm(forms.ModelForm):
#     class Meta:
#         model = LessonBooking
#         fields = ['date', 'time']  # ⬅️ teacher и subject не указываем

#     def __init__(self, *args, **kwargs):
#         self.teacher = kwargs.pop('teacher', None)
#         self.student = kwargs.pop('student', None)
#         super().__init__(*args, **kwargs)

#         # Показываем ФИО преподавателя как информативное поле
#         if self.teacher:
#             self.fields['teacher_info'] = forms.CharField(
#                 label='Преподаватель',
#                 initial=self.teacher.get_full_name(),
#                 disabled=True,
#                 required=False
#             )

#     def save(self, commit=True):
#         instance = super().save(commit=False)

#         # Устанавливаем учителя, ученика и предмет
#         if self.teacher:
#             instance.teacher = self.teacher
#             instance.subject = self.teacher.desired_subject  # можно обернуть в if
#         if self.student:
#             instance.student = self.student

#         if commit:
#             instance.save()
#         return instance
# lessons/forms.py
from django import forms
from .models import LessonBooking, TeacherAvailability

class LessonBookingForm(forms.ModelForm):
    slot = forms.ModelChoiceField(
        queryset=TeacherAvailability.objects.none(),
        label="Выберите свободное время"
    )

    class Meta:
        model = LessonBooking
        fields = ['slot']  # Убираем 'subject' из формы, оно задаётся автоматически

    def __init__(self, *args, **kwargs):
        self.student = kwargs.pop('student', None)
        self.teacher = kwargs.pop('teacher', None)
        super().__init__(*args, **kwargs)

        if self.teacher:
            self.fields['slot'].queryset = TeacherAvailability.objects.filter(
                teacher=self.teacher,
                is_booked=False
            ).order_by('date', 'time')

    def save(self, commit=True):
        booking = super().save(commit=False)
        booking.student = self.student
        booking.teacher = self.teacher

        slot = self.cleaned_data['slot']
        booking.date = slot.date
        booking.time = slot.time

        # Автоматически назначаем предмет по учителю
        # Если у учителя есть поле desired_subject или связанный предмет:
        if hasattr(self.teacher, 'desired_subject') and self.teacher.desired_subject:
            booking.subject = self.teacher.desired_subject
        else:
            # Если у тебя есть другая логика получения предмета, используй её
            # Например, если учитель может преподавать несколько предметов, нужно уточнить
            raise ValueError("У учителя не задан предмет")

        slot.is_booked = True
        slot.save()

        if commit:
            booking.save()
        return booking


from django import forms
from accounts.models import Lesson

from django import forms
from .models import HomeworkSubmission

class HomeworkSubmissionForm(forms.ModelForm):
    class Meta:
        model = HomeworkSubmission
        fields = ['file', 'comment']


