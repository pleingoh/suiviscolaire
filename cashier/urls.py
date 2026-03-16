from rest_framework.routers import DefaultRouter
from .views import CashTransactionViewSet

router = DefaultRouter()
router.register(r"transactions", CashTransactionViewSet)

urlpatterns = router.urls
