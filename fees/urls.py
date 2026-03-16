from rest_framework.routers import DefaultRouter
from .views import (
    FeePlanViewSet,
    StudentFeeAccountViewSet,
    FeeInstallmentViewSet,
    FeeReportViewSet,
)

router = DefaultRouter()
router.register(r"plans", FeePlanViewSet)
router.register(r"accounts", StudentFeeAccountViewSet)
router.register(r"installments", FeeInstallmentViewSet)

# reports
router.register(r"reports", FeeReportViewSet, basename="fee-reports")

urlpatterns = router.urls

