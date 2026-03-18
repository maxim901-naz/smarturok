# chat/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.db import models
from django.conf import settings

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.chat_id = self.scope['url_route']['kwargs']['chat_id']
        self.room_group_name = f'chat_{self.chat_id}'

        # Проверка аутентификации
        if self.scope["user"].is_anonymous:
            await self.close()
            return

        # Проверка доступа к чату
        if not await self.is_user_in_chat(self.scope["user"].id, self.chat_id):
            await self.close()
            return

        # Присоединяемся к комнату
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Покидаем комнату
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data['message']

        # Сохраняем сообщение в БД
        saved_message = await self.save_message(
            self.scope["user"].id,
            self.chat_id,
            message
        )

        # Отправляем сообщение в группу
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'sender_id': self.scope["user"].id,
                'sender_name': self.scope["user"].get_full_name() or self.scope["user"].username,
                'timestamp': saved_message['timestamp']
            }
        )

    async def chat_message(self, event):
        # Отправляем сообщение WebSocket
        await self.send(text_data=json.dumps({
            'message': event['message'],
            'sender_id': event['sender_id'],
            'sender_name': event['sender_name'],
            'timestamp': event['timestamp']
        }))

    @database_sync_to_async
    def is_user_in_chat(self, user_id, chat_id):
        from .models import Chat
        return Chat.objects.filter(
            id=chat_id
        ).filter(
            models.Q(student_id=user_id) | models.Q(teacher_id=user_id)
        ).exists()

    @database_sync_to_async
    def save_message(self, user_id, chat_id, message_text):
        from django.utils import timezone
        from django.contrib.auth import get_user_model
        from .models import Chat, Message
        
        User = get_user_model()
        chat = Chat.objects.get(id=chat_id)
        sender = User.objects.get(id=user_id)
        message = Message.objects.create(
            chat=chat,
            sender=sender,
            text=message_text,
            timestamp=timezone.now()
        )
        return {
            'timestamp': message.timestamp.isoformat()
        }