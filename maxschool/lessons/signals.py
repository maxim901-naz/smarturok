# lessons/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from accounts.models import Lesson   # твоя модель урока
from chat.models import Chat

@receiver(post_save, sender=Lesson)
def create_chat_for_lesson(sender, instance, created, **kwargs):
    if created:  # если только что создан урок
        student = instance.student
        teacher = instance.teacher
        # создаём чат, если его ещё нет
        Chat.objects.get_or_create(student=student, teacher=teacher)

