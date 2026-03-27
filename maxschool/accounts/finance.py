def get_lesson_student_price(lesson, subject=None):
    lesson_subject = subject or getattr(lesson, 'subject', None)
    amount = int(getattr(lesson, 'price_per_lesson', 0) or 0)
    if amount == 0 and lesson_subject and getattr(lesson_subject, 'price_per_lesson', 0):
        amount = int(lesson_subject.price_per_lesson)
    return max(0, amount)


def get_teacher_payout_amount_for_lesson(teacher, lesson, subject=None):
    student_price = get_lesson_student_price(lesson, subject=subject)
    if teacher and hasattr(teacher, 'calculate_lesson_payout'):
        payout_amount = int(teacher.calculate_lesson_payout(student_price))
    else:
        payout_amount = student_price
    return max(0, payout_amount)
