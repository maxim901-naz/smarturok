import json
from datetime import date, time, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import CustomUser, Subject, Lesson
from .models import LessonBooking, TeacherAvailability


class BookingFlowTests(TestCase):
    def setUp(self):
        self.subject = Subject.objects.create(name="Математика")
        self.teacher = CustomUser.objects.create_user(
            username="teacher1",
            password="pass12345",
            role="teacher",
            is_approved=True,
            is_active=True,
        )
        self.teacher.desired_subject = self.subject
        self.teacher.save()

        self.student = CustomUser.objects.create_user(
            username="student1",
            password="pass12345",
            role="student",
            is_active=True,
        )
        self.student.teachers.add(self.teacher)

    def test_assign_student_to_slot_creates_lesson_and_booking(self):
        slot = TeacherAvailability.objects.create(
            teacher=self.teacher,
            date=date.today() + timedelta(days=1),
            time=time(10, 0),
            duration_minutes=30,
            is_recurring=False,
            is_booked=False,
        )

        self.client.force_login(self.teacher)
        url = reverse("assign_student_to_slot")
        response = self.client.post(
            url,
            data=json.dumps({
                "slot_id": slot.id,
                "student_id": self.student.id,
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(Lesson.objects.filter(teacher=self.teacher, student=self.student).exists())
        self.assertTrue(LessonBooking.objects.filter(teacher=self.teacher, student=self.student).exists())

        slot.refresh_from_db()
        self.assertTrue(slot.is_booked)

    def test_delete_lesson_series(self):
        weekday = 0  # Monday
        start_date = date.today()
        end_date = start_date + timedelta(weeks=4)
        lesson_time = time(12, 0)

        rec_slot = TeacherAvailability.objects.create(
            teacher=self.teacher,
            date=None,
            weekday=weekday,
            time=lesson_time,
            duration_minutes=30,
            is_recurring=True,
            is_booked=True,
        )

        lessons = []
        for i in range(3):
            lessons.append(
                Lesson.objects.create(
                    subject=self.subject,
                    teacher=self.teacher,
                    student=self.student,
                    date=start_date + timedelta(weeks=i),
                    time=lesson_time,
                    duration_minutes=30,
                    is_recurring=True,
                    days_of_week="Monday",
                    end_date=end_date,
                )
            )

        LessonBooking.objects.create(
            student=self.student,
            teacher=self.teacher,
            subject=self.subject,
            date=start_date,
            time=lesson_time,
            is_confirmed=True,
            is_recurring=True,
        )

        self.client.force_login(self.teacher)
        url = reverse("delete_lesson")
        response = self.client.post(
            url,
            data=json.dumps({
                "lesson_id": lessons[0].id,
                "delete_type": "all",
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Lesson.objects.filter(teacher=self.teacher, student=self.student, is_recurring=True).exists())
        self.assertFalse(LessonBooking.objects.filter(teacher=self.teacher, student=self.student, is_recurring=True).exists())

        rec_slot.refresh_from_db()
        self.assertFalse(rec_slot.is_booked)
