from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/lesson/(?P<lesson_id>\d+)/$', consumers.WhiteboardConsumer.as_asgi()),
]
