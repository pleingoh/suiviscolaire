from rest_framework.routers import DefaultRouter
from .views import SchoolViewSet, SchoolYearViewSet, TermViewSet, GradeLevelViewSet, ClassRoomViewSet

router = DefaultRouter()
router.register(r"schools", SchoolViewSet)
router.register(r"school-years", SchoolYearViewSet)
router.register(r"terms", TermViewSet)
router.register(r"grade-levels", GradeLevelViewSet)
router.register(r"classes", ClassRoomViewSet)

urlpatterns = router.urls
