from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    SubjectViewSet,
    TeacherAssignmentViewSet,
    EvaluationViewSet,
    GradeViewSet,
    BulletinAPIView,
    ClassBulletinAPIView,
    BulletinPDFAPIView,
)

router = DefaultRouter()
router.register(r"subjects", SubjectViewSet)
router.register(r"teacher-assignments", TeacherAssignmentViewSet)
router.register(r"evaluations", EvaluationViewSet)
router.register(r"grades", GradeViewSet)

urlpatterns = router.urls

urlpatterns += [
    path("bulletin/", BulletinAPIView.as_view(), name="bulletin"),
    path("class-bulletin/", ClassBulletinAPIView.as_view(), name="class-bulletin"),
    path("bulletin-pdf/", BulletinPDFAPIView.as_view(), name="bulletin-pdf"),
]
