from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils.translation import gettext as _
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from .models import Student, Enrollment, StudentParent
from .serializers import StudentSerializer, EnrollmentSerializer, StudentParentSerializer


class StudentViewSet(viewsets.ModelViewSet):
    queryset = Student.objects.all()
    serializer_class = StudentSerializer
    permission_classes = [IsAuthenticated]

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

        qs = Student.objects.filter(
            enrollments__classroom_id=classroom_id,
            enrollments__school_year_id=school_year_id,
            enrollments__status="ENROLLED",
        ).distinct()

        data = self.get_serializer(qs, many=True).data
        return Response(data, status=200)


class EnrollmentViewSet(viewsets.ModelViewSet):
    queryset = Enrollment.objects.all()
    serializer_class = EnrollmentSerializer
    permission_classes = [IsAuthenticated]


class StudentParentViewSet(viewsets.ModelViewSet):
    queryset = StudentParent.objects.all()
    serializer_class = StudentParentSerializer
    permission_classes = [IsAuthenticated]
