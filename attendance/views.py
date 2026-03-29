from datetime import date as dt_date, time as dt_time

from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils.translation import gettext as _
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from .models import Attendance
from .serializers import AttendanceSerializer
from core.models import SchoolSetting
from students.models import Student, Enrollment


class AttendanceViewSet(viewsets.ModelViewSet):
    queryset = Attendance.objects.all()
    serializer_class = AttendanceSerializer
    permission_classes = [IsAuthenticated]

    # -------------------------
    # Helpers
    # -------------------------

    def _late_cutoff_time(self, student_id: int):
        student = Student.objects.select_related("school").get(id=student_id)
        setting = SchoolSetting.objects.filter(school=student.school).first()
        return setting.late_after_time if setting and setting.late_after_time else dt_time(7, 30)

    def _compute_status(self, arrival_time, cutoff_time):
        if arrival_time and cutoff_time and arrival_time > cutoff_time:
            return "LATE"
        return "PRESENT"

    # -------------------------
    # Arrivée / Sortie
    # -------------------------

    @action(detail=False, methods=["post"], url_path="checkin")
    def checkin(self, request):
        student_id = request.data.get("student")
        school_year_id = request.data.get("school_year")

        if not student_id or not school_year_id:
            return Response({"detail": _("student et school_year sont obligatoires")}, status=400)

        d = request.data.get("date") or dt_date.today().isoformat()
        method = request.data.get("method") or "MANUAL"

        t = request.data.get("arrival_time")
        if t is None:
            t = timezone.localtime().time().replace(microsecond=0)

        obj, created = Attendance.objects.get_or_create(
            student_id=student_id,
            school_year_id=school_year_id,
            date=d,
            defaults={
                "arrival_time": t,
                "arrival_method": method,
                "status": "PRESENT",
            },
        )

        if obj.arrival_time is None:
            obj.arrival_time = t
            obj.arrival_method = method

        cutoff = self._late_cutoff_time(int(student_id))
        obj.status = self._compute_status(obj.arrival_time, cutoff)
        obj.save()

        return Response(
            AttendanceSerializer(obj).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )

    @action(detail=False, methods=["post"], url_path="checkout")
    def checkout(self, request):
        student_id = request.data.get("student")
        school_year_id = request.data.get("school_year")

        if not student_id or not school_year_id:
            return Response({"detail": _("student et school_year sont obligatoires")}, status=400)

        d = request.data.get("date") or dt_date.today().isoformat()
        method = request.data.get("method") or "MANUAL"

        t = request.data.get("departure_time")
        if t is None:
            t = timezone.localtime().time().replace(microsecond=0)

        obj, _ = Attendance.objects.get_or_create(
            student_id=student_id,
            school_year_id=school_year_id,
            date=d,
            defaults={"status": "PRESENT"},
        )

        obj.departure_time = t
        obj.departure_method = method
        obj.save()

        return Response(AttendanceSerializer(obj).data, status=200)

    # -------------------------
    # Présence par classe (uniquement les pointages existants)
    # -------------------------

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
        d = request.query_params.get("date") or dt_date.today().isoformat()

        if not classroom_id or not school_year_id:
            return Response({"detail": _("classroom_id et school_year_id sont obligatoires")}, status=400)

        qs = Attendance.objects.filter(
            student__enrollments__classroom_id=classroom_id,
            school_year_id=school_year_id,
            date=d,
        ).select_related("student")

        return Response(AttendanceSerializer(qs, many=True).data, status=200)

    # -------------------------
    # Présence du jour (liste complète classe + ABSENT + compteurs)
    # -------------------------

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
        d = request.query_params.get("date") or dt_date.today().isoformat()

        if not classroom_id or not school_year_id:
            return Response({"detail": _("classroom_id et school_year_id sont obligatoires")}, status=400)

        enrollments = Enrollment.objects.filter(
            classroom_id=classroom_id,
            school_year_id=school_year_id,
            status="ENROLLED",
        ).select_related("student")

        student_ids = [e.student_id for e in enrollments]

        att_map = {
            a.student_id: a
            for a in Attendance.objects.filter(
                school_year_id=school_year_id,
                date=d,
                student_id__in=student_ids,
            )
        }

        present_count = 0
        late_count = 0
        absent_count = 0

        results = []
        for e in enrollments:
            s = e.student
            a = att_map.get(s.id)

            status_value = a.status if a else "ABSENT"

            if status_value == "PRESENT":
                present_count += 1
            elif status_value == "LATE":
                late_count += 1
            else:
                absent_count += 1

            results.append({
                "student_id": s.id,
                "student_name": f"{s.first_name} {s.last_name}",
                "date": d,
                "arrival_time": a.arrival_time if a else None,
                "departure_time": a.departure_time if a else None,
                "status": status_value,
            })

        return Response({
            "classroom_id": int(classroom_id),
            "school_year_id": int(school_year_id),
            "date": d,
            "counts": {
                "total": len(results),
                "present": present_count,
                "late": late_count,
                "absent": absent_count,
            },
            "results": results,
        }, status=200)
