from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import EmailOrPhoneTokenObtainPairSerializer


class EmailOrPhoneTokenObtainPairView(TokenObtainPairView):
    serializer_class = EmailOrPhoneTokenObtainPairSerializer
