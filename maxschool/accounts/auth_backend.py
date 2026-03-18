from django.contrib.auth.backends import ModelBackend

class ApprovedTeacherBackend(ModelBackend):
    def user_can_authenticate(self, user):
        is_active = super().user_can_authenticate(user)
        if not is_active:
            return False
        if user.role == 'teacher' and not user.is_approved:
            return False
        return True
