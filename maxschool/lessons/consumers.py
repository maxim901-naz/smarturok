# # lessons/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer

class WhiteboardConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.lesson_id = self.scope['url_route']['kwargs']['lesson_id']
        self.room_group_name = f'lesson_{self.lesson_id}'

        # Присоединяемся к группе урока
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # Убираемся из группы при отключении
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)

        # Если это команда очистки доски, добавляем тип
        if 'type' not in data:
            data['type'] = 'draw'

        # Отправляем всем в группе
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'whiteboard_message',
                'data': data
            }
        )

    # Получаем сообщение от группы
    async def whiteboard_message(self, event):
        data = event['data']
        await self.send(text_data=json.dumps(data))
