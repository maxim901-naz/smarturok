from django.apps import AppConfig


class LessonsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'lessons'
# lessons/apps.py

    def ready(self):
        import lessons.signals  # подключаем наш сигнал
