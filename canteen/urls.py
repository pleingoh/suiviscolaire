from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import CanteenPlanViewSet, CanteenSubscriptionViewSet, CanteenAttendanceViewSet

router = DefaultRouter()
router.register(r"plans", CanteenPlanViewSet)
router.register(r"subscriptions", CanteenSubscriptionViewSet)
router.register(r"attendance", CanteenAttendanceViewSet)

urlpatterns = router.urls
