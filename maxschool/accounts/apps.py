from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        import accounts.signals

# class LessonsConfig(AppConfig):
#     default_auto_field = 'django.db.models.BigAutoField'
#     name = 'lessons'

#     def ready(self):
#         import lessons.signals
