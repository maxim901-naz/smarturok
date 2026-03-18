from django.contrib import admin
from .models import Chat, Message

@admin.register(Chat)
class ChatAdmin(admin.ModelAdmin):
    list_display = ('id', 'student', 'teacher', 'created_at')
    search_fields = ('student__username', 'teacher__username')

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'chat', 'sender', 'timestamp', 'is_read')
    search_fields = ('sender__username', 'text')
    list_filter = ('is_read',)
