from rest_framework.routers import DefaultRouter
from .views import StudentViewSet, EnrollmentViewSet, StudentParentViewSet

router = DefaultRouter()
router.register(r"students", StudentViewSet)
router.register(r"enrollments", EnrollmentViewSet)
router.register(r"student-parents", StudentParentViewSet)

urlpatterns = router.urls
