# chat/models.py
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError

# Удалите эту строку:
# User = get_user_model()

class Chat(models.Model):
    """
    Диалог между учеником и учителем (один-на-один).
    """
    # Используйте settings.AUTH_USER_MODEL вместо get_user_model()
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="student_chats")
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="teacher_chats")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'teacher')  # один чат на пару

    def clean(self):
        if self.student_id == self.teacher_id:
            raise ValidationError("Участники чата должны быть разными пользователями.")

    def __str__(self):
        return f"Чат {self.student} ↔ {self.teacher}"

class Message(models.Model):
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name="messages")
    # Используйте settings.AUTH_USER_MODEL вместо get_user_model()
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    text = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.sender}: {self.text[:30]}"