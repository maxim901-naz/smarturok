from django.urls import path
from . import views

app_name = "chat"

urlpatterns = [
    path("", views.chat_list, name="list"),
    path("<int:chat_id>/", views.chat_detail, name="detail"),
    path("start/<int:user_id>/", views.chat_start, name="start"),
]
