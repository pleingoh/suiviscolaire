from datetime import date as dt_date

from django.db.models import Count
from django.utils.translation import gettext as _
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.access import ensure_same_school, ensure_user_school, is_global_admin
from students.models import Enrollment

from .models import CanteenAttendance, CanteenPlan, CanteenSubscription
from .serializers import CanteenAttendanceSerializer, CanteenPlanSerializer, CanteenSubscriptionSerializer


class CanteenPlanViewSet(viewsets.ModelViewSet):
    queryset = CanteenPlan.objects.all()
    serializer_class = CanteenPlanSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = CanteenPlan.objects.all()
        if is_global_admin(self.request.user):
            return queryset
        return queryset.filter(school=ensure_user_school(self.request.user))

    def perform_create(self, serializer):
        ensure_same_school(self.request.user, serializer.validated_data["school"])
        serializer.save()


class CanteenSubscriptionViewSet(viewsets.ModelViewSet):
    queryset = CanteenSubscription.objects.all()
    serializer_class = CanteenSubscriptionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = CanteenSubscription.objects.all()
        if is_global_admin(self.request.user):
            return queryset
        return queryset.filter(student__school=ensure_user_school(self.request.user)).distinct()

    def perform_create(self, serializer):
        ensure_same_school(self.request.user, serializer.validated_data["student"].school)
        ensure_same_school(self.request.user, serializer.validated_data["plan"].school)
        serializer.save()

    @action(detail=True, methods=["post"], url_path="mark-paid")
    def mark_paid(self, request, pk=None):
        subscription = self.get_object()
        if subscription.status != "PAID":
            subscription.status = "PAID"
            subscription.paid_at = dt_date.today()
            subscription.save()
        return Response(CanteenSubscriptionSerializer(subscription).data, status=200)

    @extend_schema(
        parameters=[
            OpenApiParameter(name="student_id", type=OpenApiTypes.INT, required=True),
            OpenApiParameter(name="school_year_id", type=OpenApiTypes.INT, required=True),
            OpenApiParameter(name="month", type=OpenApiTypes.DATE, required=True),
        ]
    )
    @action(detail=False, methods=["get"], url_path="is-active")
    def is_active(self, request):
        student_id = request.query_params.get("student_id")
        school_year_id = request.query_params.get("school_year_id")
        month = request.query_params.get("month")
        if not student_id or not school_year_id or not month:
            return Response({"detail": _("student_id, school_year_id, month sont obligatoires")}, status=400)

        queryset = self.get_queryset().filter(
            student_id=student_id,
            school_year_id=school_year_id,
            month=month,
            status="PAID",
        )
        return Response({"active": queryset.exists()}, status=200)


class CanteenAttendanceViewSet(viewsets.ModelViewSet):
    queryset = CanteenAttendance.objects.all()
    serializer_class = CanteenAttendanceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = CanteenAttendance.objects.all()
        if is_global_admin(self.request.user):
            return queryset
        return queryset.filter(student__school=ensure_user_school(self.request.user)).distinct()

    def perform_create(self, serializer):
        ensure_same_school(self.request.user, serializer.validated_data["student"].school)
        serializer.save()

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
            enrollments = enrollments.filter(student__school=ensure_user_school(request.user))

        student_ids = [enrollment.student_id for enrollment in enrollments]
        month_first = f"{date_value[:7]}-01"

        paid_students = set(
            CanteenSubscription.objects.filter(
                school_year_id=school_year_id,
                month=month_first,
                status="PAID",
                student_id__in=student_ids,
            ).values_list("student_id", flat=True)
        )
        served_map = {
            item.student_id: item
            for item in self.get_queryset().filter(
                school_year_id=school_year_id,
                date=date_value,
                student_id__in=student_ids,
            )
        }

        results = []
        subscribed_count = not_subscribed_count = served_count = 0

        for enrollment in enrollments:
            student = enrollment.student
            served_item = served_map.get(student.id)
            is_subscribed = student.id in paid_students
            is_served = bool(served_item)

            subscribed_count += int(is_subscribed)
            not_subscribed_count += int(not is_subscribed)
            served_count += int(is_served)

            results.append(
                {
                    "student_id": student.id,
                    "student_name": f"{student.first_name} {student.last_name}",
                    "date": date_value,
                    "subscribed": is_subscribed,
                    "served": is_served,
                    "served_status": served_item.status if served_item else None,
                }
            )

        return Response(
            {
                "date": date_value,
                "counts": {
                    "total": len(results),
                    "subscribed": subscribed_count,
                    "not_subscribed": not_subscribed_count,
                    "served": served_count,
                },
                "results": results,
            },
            status=200,
        )

    @action(detail=False, methods=["post"], url_path="serve")
    def serve(self, request):
        student_id = request.data.get("student")
        school_year_id = request.data.get("school_year")
        date_value = request.data.get("date") or dt_date.today().isoformat()
        if not student_id or not school_year_id:
            return Response({"detail": _("student et school_year sont obligatoires")}, status=400)

        student = Enrollment.objects.select_related("student__school").filter(student_id=student_id).first()
        if not student:
            return Response({"detail": _("Eleve introuvable")}, status=404)
        ensure_same_school(request.user, student.student.school)

        month_first = f"{date_value[:7]}-01"
        paid = CanteenSubscription.objects.filter(
            student_id=student_id,
            school_year_id=school_year_id,
            month=month_first,
            status="PAID",
        )
        if not is_global_admin(request.user):
            paid = paid.filter(student__school=ensure_user_school(request.user))
        if not paid.exists():
            return Response({"detail": _("Forfait cantine non paye pour ce mois")}, status=403)

        attendance, created = CanteenAttendance.objects.get_or_create(
            student_id=student_id,
            school_year_id=school_year_id,
            date=date_value,
            defaults={"status": "SERVED"},
        )
        if attendance.status != "SERVED":
            attendance.status = "SERVED"
            attendance.save()

        return Response({"served": True, "attendance_id": attendance.id, "created": created}, status=200)

    @extend_schema(
        parameters=[
            OpenApiParameter(name="classroom_id", type=OpenApiTypes.INT, required=True),
            OpenApiParameter(name="school_year_id", type=OpenApiTypes.INT, required=True),
            OpenApiParameter(name="month", type=OpenApiTypes.DATE, required=True),
        ]
    )
    @action(detail=False, methods=["get"], url_path="class-month-report")
    def class_month_report(self, request):
        classroom_id = request.query_params.get("classroom_id")
        school_year_id = request.query_params.get("school_year_id")
        month = request.query_params.get("month")
        if not classroom_id or not school_year_id or not month:
            return Response({"detail": _("classroom_id, school_year_id, month sont obligatoires")}, status=400)

        enrollments = Enrollment.objects.filter(
            classroom_id=classroom_id,
            school_year_id=school_year_id,
            status="ENROLLED",
        ).select_related("student")
        if not is_global_admin(request.user):
            enrollments = enrollments.filter(student__school=ensure_user_school(request.user))

        student_ids = [enrollment.student_id for enrollment in enrollments]
        paid_students = set(
            CanteenSubscription.objects.filter(
                school_year_id=school_year_id,
                month=month,
                status="PAID",
                student_id__in=student_ids,
            ).values_list("student_id", flat=True)
        )
        served_counts = dict(
            self.get_queryset()
            .filter(
                school_year_id=school_year_id,
                date__startswith=month[:7],
                student_id__in=student_ids,
                status="SERVED",
            )
            .values("student_id")
            .annotate(c=Count("id"))
            .values_list("student_id", "c")
        )

        results = [
            {
                "student_id": enrollment.student.id,
                "student_name": f"{enrollment.student.first_name} {enrollment.student.last_name}",
                "paid": enrollment.student.id in paid_students,
                "served_days": served_counts.get(enrollment.student.id, 0),
            }
            for enrollment in enrollments
        ]

        return Response(
            {
                "classroom_id": int(classroom_id),
                "school_year_id": int(school_year_id),
                "month": month,
                "results": results,
            },
            status=200,
        )
