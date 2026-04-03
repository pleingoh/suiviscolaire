from datetime import date as dt_date, time as dt_time

from django.utils import timezone
from django.utils.translation import gettext as _
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.access import ensure_same_school, ensure_user_school, is_global_admin
from core.models import SchoolSetting
from students.models import Enrollment, Student

from .models import Attendance
from .serializers import AttendanceSerializer


class AttendanceViewSet(viewsets.ModelViewSet):
    serializer_class = AttendanceSerializer
    permission_classes = [IsAuthenticated]
    queryset = Attendance.objects.all()

    def get_queryset(self):
        queryset = Attendance.objects.all()
        if is_global_admin(self.request.user):
            return queryset
        school = ensure_user_school(self.request.user)
        return queryset.filter(student__school=school).distinct()

    def _get_student(self, student_id):
        student = Student.objects.select_related("school").get(id=student_id)
        ensure_same_school(self.request.user, student.school)
        return student

    def _late_cutoff_time(self, student_id: int):
        student = self._get_student(student_id)
        setting = SchoolSetting.objects.filter(school=student.school).first()
        return setting.late_after_time if setting and setting.late_after_time else dt_time(7, 30)

    def _compute_status(self, arrival_time, cutoff_time):
        if arrival_time and cutoff_time and arrival_time > cutoff_time:
            return "LATE"
        return "PRESENT"

    @action(detail=False, methods=["post"], url_path="checkin")
    def checkin(self, request):
        student_id = request.data.get("student")
        school_year_id = request.data.get("school_year")
        if not student_id or not school_year_id:
            return Response({"detail": _("student et school_year sont obligatoires")}, status=400)

        student = self._get_student(int(student_id))
        ensure_same_school(request.user, student.school)

        date_value = request.data.get("date") or dt_date.today().isoformat()
        method = request.data.get("method") or "MANUAL"
        arrival_time = request.data.get("arrival_time") or timezone.localtime().time().replace(microsecond=0)

        attendance, created = Attendance.objects.get_or_create(
            student_id=student_id,
            school_year_id=school_year_id,
            date=date_value,
            defaults={"arrival_time": arrival_time, "arrival_method": method, "status": "PRESENT"},
        )

        if attendance.arrival_time is None:
            attendance.arrival_time = arrival_time
            attendance.arrival_method = method

        attendance.status = self._compute_status(attendance.arrival_time, self._late_cutoff_time(int(student_id)))
        attendance.save()

        return Response(
            AttendanceSerializer(attendance).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"], url_path="checkout")
    def checkout(self, request):
        student_id = request.data.get("student")
        school_year_id = request.data.get("school_year")
        if not student_id or not school_year_id:
            return Response({"detail": _("student et school_year sont obligatoires")}, status=400)

        self._get_student(int(student_id))
        date_value = request.data.get("date") or dt_date.today().isoformat()
        method = request.data.get("method") or "MANUAL"
        departure_time = request.data.get("departure_time") or timezone.localtime().time().replace(microsecond=0)

        attendance, _ = Attendance.objects.get_or_create(
            student_id=student_id,
            school_year_id=school_year_id,
            date=date_value,
            defaults={"status": "PRESENT"},
        )
        attendance.departure_time = departure_time
        attendance.departure_method = method
        attendance.save()
        return Response(AttendanceSerializer(attendance).data, status=200)

    @extend_schema(
        parameters=[
            OpenApiParameter(name="classroom_id", type=OpenApiTypes.INT, required=True),
            OpenApiParameter(name="school_year_id", type=OpenApiTypes.INT, required=True),
            OpenApiParameter(name="date", type=OpenApiTypes.DATE, required=False),
        ]
    )
    @action(detail=False, methods=["get"], url_path="by-class")
    def by_class(self, request):
        classroom_id = request.query_params.get("classroom_id")
        school_year_id = request.query_params.get("school_year_id")
        date_value = request.query_params.get("date") or dt_date.today().isoformat()

        if not classroom_id or not school_year_id:
            return Response({"detail": _("classroom_id et school_year_id sont obligatoires")}, status=400)

        queryset = self.get_queryset().filter(
            student__enrollments__classroom_id=classroom_id,
            school_year_id=school_year_id,
            date=date_value,
        ).select_related("student")
        return Response(AttendanceSerializer(queryset, many=True).data, status=200)

    @extend_schema(
        parameters=[
            OpenApiParameter(name="classroom_id", type=OpenApiTypes.INT, required=True),
            OpenApiParameter(name="school_year_id", type=OpenApiTypes.INT, required=True),
            OpenApiParameter(name="date", type=OpenApiTypes.DATE, required=False),
        ]
    )
    @action(detail=False, methods=["get"], url_path="class-today")
    def class_today(self, request):
        classroom_id = request.query_params.get("classroom_id")
        school_year_id = request.query_params.get("school_year_id")
        date_value = request.query_params.get("date") or dt_date.today().isoformat()

        if not classroom_id or not school_year_id:
            return Response({"detail": _("classroom_id et school_year_id sont obligatoires")}, status=400)

        enrollments = Enrollment.objects.filter(
            classroom_id=classroom_id,
            school_year_id=school_year_id,
            status="ENROLLED",
        ).select_related("student")

        if not is_global_admin(request.user):
            school = ensure_user_school(request.user)
            enrollments = enrollments.filter(student__school=school)

        student_ids = [enrollment.student_id for enrollment in enrollments]
        attendance_map = {
            attendance.student_id: attendance
            for attendance in self.get_queryset().filter(
                school_year_id=school_year_id,
                date=date_value,
                student_id__in=student_ids,
            )
        }

        present_count = late_count = absent_count = 0
        results = []

        for enrollment in enrollments:
            student = enrollment.student
            attendance = attendance_map.get(student.id)
            status_value = attendance.status if attendance else "ABSENT"

            if status_value == "PRESENT":
                present_count += 1
            elif status_value == "LATE":
                late_count += 1
            else:
                absent_count += 1

            results.append(
                {
                    "student_id": student.id,
                    "student_name": f"{student.first_name} {student.last_name}",
                    "date": date_value,
                    "arrival_time": attendance.arrival_time if attendance else None,
                    "departure_time": attendance.departure_time if attendance else None,
                    "status": status_value,
                }
            )

        return Response(
            {
                "classroom_id": int(classroom_id),
                "school_year_id": int(school_year_id),
                "date": date_value,
                "counts": {
                    "total": len(results),
                    "present": present_count,
                    "late": late_count,
                    "absent": absent_count,
                },
                "results": results,
            },
            status=200,
        )
