from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _
from rest_framework import exceptions, serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class EmailOrPhoneTokenObtainPairSerializer(TokenObtainPairSerializer):
    email = serializers.EmailField(required=False)
    phone = serializers.CharField(required=False)
    identifier = serializers.CharField(required=False)
    password = serializers.CharField(write_only=True)

    default_error_messages = {
        "no_active_account": _("Aucun compte actif ne correspond a ces identifiants."),
        "missing_identifier": _("Veuillez fournir un email ou un telephone."),
    }

    def validate(self, attrs):
        identifier = attrs.get("email") or attrs.get("phone") or attrs.get("identifier")
        password = attrs.get("password")

        if not identifier:
            raise exceptions.AuthenticationFailed(self.error_messages["missing_identifier"], "missing_identifier")

        self.user = authenticate(
            request=self.context.get("request"),
            username=identifier,
            password=password,
        )

        if not self.user:
            raise exceptions.AuthenticationFailed(self.error_messages["no_active_account"], "no_active_account")

        refresh = self.get_token(self.user)
        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }
