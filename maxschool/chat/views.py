from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Max, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.clickjacking import xframe_options_sameorigin

from lessons.models import LessonBooking

from .models import Chat


def _user_chats_queryset(user):
    return (
        Chat.objects.filter(Q(student=user) | Q(teacher=user))
        .select_related("student", "teacher")
        .annotate(
            last_time=Max("messages__timestamp"),
            unread_count=Count(
                "messages",
                filter=Q(messages__is_read=False) & ~Q(messages__sender=user),
            ),
        )
        .order_by("-last_time", "-id")
    )


@login_required
def chat_list(request):
    first_chat = _user_chats_queryset(request.user).first()
    if first_chat:
        return redirect("chat:detail", chat_id=first_chat.id)

    if getattr(request.user, "role", None) == "student":
        return redirect("student_dashboard")
    if getattr(request.user, "role", None) == "teacher":
        return redirect("teacher_dashboard")
    return redirect("dashboard")


@xframe_options_sameorigin
@login_required
def chat_detail(request, chat_id):
    chat = get_object_or_404(Chat, id=chat_id)
    if request.user not in (chat.student, chat.teacher):
        return redirect("chat:list")

    messages_qs = chat.messages.select_related("sender").all()
    chat.messages.filter(~Q(sender=request.user), is_read=False).update(is_read=True)
    embedded = request.GET.get("embedded") == "1"
    template_name = "chat/chat_embed.html" if embedded else "chat/chat_detail.html"

    return render(
        request,
        template_name,
        {
            "chat": chat,
            "messages": messages_qs,
            "embedded": embedded,
        },
    )


@login_required
def chat_start(request, user_id):
    User = get_user_model()

    other = get_object_or_404(User, id=user_id)
    if request.user == other:
        return redirect("chat:list")

    # Явно фиксируем роли в чате: student <-> teacher.
    student = None
    teacher = None
    if request.user.role == "student" and other.role == "teacher":
        student, teacher = request.user, other
    elif request.user.role == "teacher" and other.role == "student":
        student, teacher = other, request.user
    else:
        messages.error(request, "Чат доступен только между учеником и преподавателем.")
        return redirect("dashboard")

    # Проверяем, есть ли урок между этой парой ролей.
    has_lesson = LessonBooking.objects.filter(student=student, teacher=teacher).exists()

    if not has_lesson:
        messages.error(request, "Чат доступен только после оформления урока с этим пользователем.")
        return redirect("dashboard")

    # Роли фиксированы, создаем (или берем) единственный чат пары.
    chat, _ = Chat.objects.get_or_create(student=student, teacher=teacher)
    target_url = reverse("chat:detail", kwargs={"chat_id": chat.id})
    if request.GET.get("embedded") == "1":
        target_url = f"{target_url}?embedded=1"
    return redirect(target_url)
