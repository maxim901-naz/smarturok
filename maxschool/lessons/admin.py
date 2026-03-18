
from django.contrib import admin
from .models import LessonBooking

@admin.register(LessonBooking)
class LessonBookingAdmin(admin.ModelAdmin):
    list_display = ('student', 'teacher', 'subject', 'date', 'time', 'is_confirmed')
    list_filter = ('subject', 'date', 'is_confirmed')
    search_fields = ('student__username', 'teacher__username')

from django.contrib import admin


