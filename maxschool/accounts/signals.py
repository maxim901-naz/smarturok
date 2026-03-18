from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Lesson, BalanceTransaction, TeacherFinanceEntry


@receiver(post_save, sender=Lesson)
def deduct_balance_on_complete(sender, instance, created, **kwargs):
    if instance.lesson_status != 'conducted':
        return

    # Prevent double списание
    if BalanceTransaction.objects.filter(lesson=instance, direction='debit').exists():
        return

    student = instance.student
    if not student:
        return

    if student.balance > 0:
        student.balance -= 1
        student.save(update_fields=['balance'])
        BalanceTransaction.objects.create(
            user=student,
            lesson=instance,
            direction='debit',
            amount=1,
            note='Списание за завершенный урок'
        )

        amount_value = instance.price_per_lesson or 0
        if amount_value == 0 and instance.subject and getattr(instance.subject, 'price_per_lesson', 0):
            amount_value = instance.subject.price_per_lesson
        subject_name = instance.subject.name if getattr(instance, "subject", None) else ""
        if getattr(instance, "student", None):
            student_name = instance.student.get_full_name() or instance.student.username
        else:
            student_name = ""
        TeacherFinanceEntry.objects.create(
            teacher=instance.teacher,
            lesson=instance,
            subject_name=subject_name,
            student_name=student_name,
            lesson_date=instance.date,
            lesson_time=instance.time,
            lesson_status=getattr(instance, "lesson_status", "") or "",
            amount=amount_value
        )
