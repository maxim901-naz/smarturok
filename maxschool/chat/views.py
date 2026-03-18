# chat/views.py
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Max, Count
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth import get_user_model
from .models import Chat, Message
from lessons.models import LessonBooking

@login_required
def chat_list(request):
    User = get_user_model()
    # Оптимизированный запрос с аннотацией количества непрочитанных сообщений
    chats = Chat.objects.filter(
        Q(student=request.user) | Q(teacher=request.user)
    ).annotate(
        last_time=Max('messages__timestamp'),
        unread_count=Count('messages', 
            filter=Q(messages__is_read=False) & 
                   ~Q(messages__sender=request.user)
        )
    ).order_by('-last_time', '-id')
    
    return render(request, "chat/chat_list.html", {"chats": chats})

@login_required
def chat_detail(request, chat_id):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    chat = get_object_or_404(Chat, id=chat_id)
    if request.user not in (chat.student, chat.teacher):
        return redirect("chat:list")

    messages = chat.messages.select_related('sender').all()
    chat.messages.filter(~Q(sender=request.user), is_read=False).update(is_read=True)

    return render(request, "chat/chat_detail.html", {
        "chat": chat,
        "messages": messages,
    })

@login_required
def chat_start(request, user_id):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    other = get_object_or_404(User, id=user_id)
    if request.user == other:
        return redirect("chat:list")

    # Явно фиксируем роли в чате: student <-> teacher.
    student = None
    teacher = None
    if request.user.role == 'student' and other.role == 'teacher':
        student, teacher = request.user, other
    elif request.user.role == 'teacher' and other.role == 'student':
        student, teacher = other, request.user
    else:
        return render(request, "chat/no_access.html", {"other_user": other})

    # Проверяем, есть ли урок между этой парой ролей.
    has_lesson = LessonBooking.objects.filter(student=student, teacher=teacher).exists()

    if not has_lesson:
        return render(request, "chat/no_access.html", {"other_user": other})

    # Роли фиксированы, создаем (или берем) единственный чат пары.
    chat, _ = Chat.objects.get_or_create(student=student, teacher=teacher)

    return redirect("chat:detail", chat_id=chat.id)
