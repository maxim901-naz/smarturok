from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Lesson, BalanceTransaction, TeacherFinanceEntry
from .finance import get_teacher_payout_amount_for_lesson


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

        amount_value = get_teacher_payout_amount_for_lesson(
            instance.teacher,
            instance,
            subject=instance.subject,
        )
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
