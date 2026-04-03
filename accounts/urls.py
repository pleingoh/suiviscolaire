from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .auth_views import EmailOrPhoneTokenObtainPairView
from .views import MeView

urlpatterns = [
    path("login/", EmailOrPhoneTokenObtainPairView.as_view(), name="login"),
    path("refresh/", TokenRefreshView.as_view(), name="refresh"),
    path("me/", MeView.as_view(), name="me"),
]
