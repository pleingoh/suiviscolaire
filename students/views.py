from django.utils.translation import gettext as _
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.access import ensure_same_school, ensure_user_school, is_global_admin

from .models import Enrollment, Student, StudentParent
from .serializers import EnrollmentSerializer, StudentParentSerializer, StudentSerializer


class SchoolScopedViewSetMixin:
    school_lookup = None

    def get_queryset(self):
        queryset = self.queryset.all()
        if is_global_admin(self.request.user):
            return queryset
        school = ensure_user_school(self.request.user)
        return queryset.filter(**{self.school_lookup: school}).distinct()


class StudentViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = Student.objects.all()
    serializer_class = StudentSerializer
    permission_classes = [IsAuthenticated]
    school_lookup = "school"

    def perform_create(self, serializer):
        ensure_same_school(self.request.user, serializer.validated_data["school"])
        serializer.save()

    @extend_schema(
        parameters=[
            OpenApiParameter(name="classroom_id", type=OpenApiTypes.INT, required=True),
            OpenApiParameter(name="school_year_id", type=OpenApiTypes.INT, required=True),
        ]
    )
    @action(detail=False, methods=["get"], url_path="by-class")
    def by_class(self, request):
        classroom_id = request.query_params.get("classroom_id")
        school_year_id = request.query_params.get("school_year_id")

        if not classroom_id or not school_year_id:
            return Response({"detail": _("classroom_id et school_year_id sont obligatoires")}, status=400)

        queryset = self.get_queryset().filter(
            enrollments__classroom_id=classroom_id,
            enrollments__school_year_id=school_year_id,
            enrollments__status="ENROLLED",
        ).distinct()
        return Response(self.get_serializer(queryset, many=True).data, status=200)


class EnrollmentViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = Enrollment.objects.all()
    serializer_class = EnrollmentSerializer
    permission_classes = [IsAuthenticated]
    school_lookup = "student__school"

    def perform_create(self, serializer):
        student = serializer.validated_data["student"]
        school_year = serializer.validated_data["school_year"]
        classroom = serializer.validated_data["classroom"]
        ensure_same_school(self.request.user, student.school)
        ensure_same_school(self.request.user, school_year.school)
        ensure_same_school(self.request.user, classroom.school_year.school)
        serializer.save()


class StudentParentViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = StudentParent.objects.all()
    serializer_class = StudentParentSerializer
    permission_classes = [IsAuthenticated]
    school_lookup = "student__school"

    def perform_create(self, serializer):
        student = serializer.validated_data["student"]
        parent = serializer.validated_data["parent"]
        ensure_same_school(self.request.user, student.school)
        if parent.school_id:
            ensure_same_school(self.request.user, parent.school)
        serializer.save()
