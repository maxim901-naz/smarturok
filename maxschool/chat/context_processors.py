from django.db.models import Count, Max, Q
from django.urls import reverse

from .models import Chat


def chat_widget_context(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {}

    role = getattr(user, "role", None)
    if role not in {"student", "teacher"}:
        return {}

    user_chats = list(
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

    chat_unread_total = sum((getattr(c, "unread_count", 0) or 0) for c in user_chats)
    try:
        chat_empty_url = reverse("teachers_list" if role == "student" else "my_students")
    except Exception:
        chat_empty_url = "/"

    return {
        "user_chats": user_chats,
        "chat_unread_total": chat_unread_total,
        "chat_empty_url": chat_empty_url,
    }
