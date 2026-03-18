import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings

from accounts.models import Lesson

MAX_WS_MESSAGE_BYTES = int(getattr(settings, "WHITEBOARD_WS_MAX_MESSAGE_BYTES", 2_500_000))
MAX_WS_IMAGE_DATA_URL_LENGTH = int(getattr(settings, "WHITEBOARD_WS_MAX_IMAGE_DATA_URL_LENGTH", 1_500_000))
ALLOWED_EVENT_TYPES = {
    "draw_line",
    "draw_shape",
    "draw_text",
    "draw_image",
    "update_image",
    "clear",
    "replace_board_state",
    "create_board",
    "delete_board",
    "tool_change",
}


class WhiteboardConsumer(AsyncWebsocketConsumer):
    @database_sync_to_async
    def _get_permissions(self, user, lesson_id):
        if not user or not user.is_authenticated:
            return False, False
        try:
            lesson = Lesson.objects.select_related("teacher", "student").get(id=lesson_id)
        except Lesson.DoesNotExist:
            return False, False

        is_teacher = bool(user == lesson.teacher or user.is_superuser)
        has_access = bool(is_teacher or user == lesson.student)
        return has_access, is_teacher

    async def connect(self):
        self.lesson_id = self.scope["url_route"]["kwargs"]["lesson_id"]
        self.room_group_name = f"lesson_{self.lesson_id}"
        self.can_manage_boards = False

        user = self.scope.get("user")
        has_access, is_teacher = await self._get_permissions(user, self.lesson_id)
        if not has_access:
            await self.close(code=4403)
            return
        self.can_manage_boards = is_teacher

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        if not isinstance(text_data, str):
            return
        if len(text_data.encode("utf-8")) > MAX_WS_MESSAGE_BYTES:
            return

        try:
            data = json.loads(text_data)
        except (TypeError, json.JSONDecodeError):
            return

        if not isinstance(data, dict):
            return

        event_type = data.get("type")
        if not isinstance(event_type, str):
            return
        event_type = event_type.strip()
        if event_type not in ALLOWED_EVENT_TYPES:
            return
        data["type"] = event_type

        if event_type == "draw_image":
            image_payload = data.get("image")
            if not isinstance(image_payload, dict):
                return
            src = image_payload.get("src")
            if not isinstance(src, str) or not src:
                return
            if len(src) > MAX_WS_IMAGE_DATA_URL_LENGTH:
                return

        # Only lesson teacher can manage boards.
        if event_type in {"create_board", "delete_board"} and not self.can_manage_boards:
            return

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "whiteboard_message",
                "data": data,
            },
        )

    async def whiteboard_message(self, event):
        data = event["data"]
        await self.send(text_data=json.dumps(data))
