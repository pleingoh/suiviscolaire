from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q


class EmailOrPhoneBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        identifier = username or kwargs.get("email") or kwargs.get("phone") or kwargs.get("identifier")
        if not identifier or not password:
            return None

        User = get_user_model()
        try:
            user = User.objects.get(Q(phone=identifier) | Q(email__iexact=identifier))
        except User.DoesNotExist:
            return None
        except User.MultipleObjectsReturned:
            user = User.objects.filter(Q(phone=identifier) | Q(email__iexact=identifier)).order_by("id").first()

        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
