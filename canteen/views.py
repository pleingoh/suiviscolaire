from datetime import date as dt_date

from django.db.models import Count

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils.translation import gettext as _
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from .models import CanteenPlan, CanteenSubscription, CanteenAttendance
from .serializers import (
    CanteenPlanSerializer,
    CanteenSubscriptionSerializer,
    CanteenAttendanceSerializer,
)


# -------------------------
# Plans (forfait)
# -------------------------

class CanteenPlanViewSet(viewsets.ModelViewSet):
    queryset = CanteenPlan.objects.all()
    serializer_class = CanteenPlanSerializer
    permission_classes = [IsAuthenticated]


# -------------------------
# Subscriptions (abonnements)
# -------------------------

class CanteenSubscriptionViewSet(viewsets.ModelViewSet):
    queryset = CanteenSubscription.objects.all()
    serializer_class = CanteenSubscriptionSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=["post"], url_path="mark-paid")
    def mark_paid(self, request, pk=None):
        """
        Marque un abonnement comme payé.
        (MVP : paiement manuel / caisse)
        """
        sub = self.get_object()
        if sub.status != "PAID":
            sub.status = "PAID"
            sub.paid_at = dt_date.today()
            sub.save()
        return Response(CanteenSubscriptionSerializer(sub).data, status=200)

    @extend_schema(
        parameters=[
            OpenApiParameter(name="student_id", type=OpenApiTypes.INT, required=True),
            OpenApiParameter(name="school_year_id", type=OpenApiTypes.INT, required=True),
            OpenApiParameter(name="month", type=OpenApiTypes.DATE, required=True),
        ]
    )
    @action(detail=False, methods=["get"], url_path="is-active")
    def is_active(self, request):
        """
        Vérifie si un élève a payé la cantine pour un mois donné.
        month = 1er jour du mois (ex: 2026-02-01)
        """
        student_id = request.query_params.get("student_id")
        school_year_id = request.query_params.get("school_year_id")
        month = request.query_params.get("month")

        if not student_id or not school_year_id or not month:
            return Response({"detail": _("student_id, school_year_id, month sont obligatoires")}, status=400)

        exists = CanteenSubscription.objects.filter(
            student_id=student_id,
            school_year_id=school_year_id,
            month=month,
            status="PAID",
        ).exists()

        return Response({"active": bool(exists)}, status=200)


# -------------------------
# Attendance Cantine
# -------------------------

class CanteenAttendanceViewSet(viewsets.ModelViewSet):
    queryset = CanteenAttendance.objects.all()
    serializer_class = CanteenAttendanceSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter(name="classroom_id", type=OpenApiTypes.INT, required=True),
            OpenApiParameter(name="school_year_id", type=OpenApiTypes.INT, required=True),
            OpenApiParameter(name="date", type=OpenApiTypes.DATE, required=False),
        ]
    )
    @action(detail=False, methods=["get"], url_path="class-today")
    def class_today(self, request):
        """
        Liste complète des élèves de la classe + statut cantine du jour.
        - subscribed : forfait du mois payé
        - served : a mangé aujourd'hui
        """
        from students.models import Enrollment

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

        month_first = f"{d[:7]}-01"

        paid_students = set(
            CanteenSubscription.objects.filter(
                school_year_id=school_year_id,
                month=month_first,
                status="PAID",
                student_id__in=student_ids,
            ).values_list("student_id", flat=True)
        )

        served_map = {
            a.student_id: a
            for a in CanteenAttendance.objects.filter(
                school_year_id=school_year_id,
                date=d,
                student_id__in=student_ids,
            )
        }

        subscribed_count = 0
        not_subscribed_count = 0
        served_count = 0

        results = []
        for e in enrollments:
            s = e.student
            served_obj = served_map.get(s.id)

            is_subscribed = s.id in paid_students
            is_served = bool(served_obj)

            if is_subscribed:
                subscribed_count += 1
            else:
                not_subscribed_count += 1

            if is_served:
                served_count += 1

            results.append({
                "student_id": s.id,
                "student_name": f"{s.first_name} {s.last_name}",
                "date": d,
                "subscribed": is_subscribed,
                "served": is_served,
                "served_status": served_obj.status if served_obj else None,
            })

        return Response({
            "date": d,
            "counts": {
                "total": len(results),
                "subscribed": subscribed_count,
                "not_subscribed": not_subscribed_count,
                "served": served_count,
            },
            "results": results,
        }, status=200)

    @action(detail=False, methods=["post"], url_path="serve")
    def serve(self, request):
        """
        Sert un élève à la cantine.
        Refuse si forfait du mois non payé.
        """
        student_id = request.data.get("student")
        school_year_id = request.data.get("school_year")
        d = request.data.get("date") or dt_date.today().isoformat()

        if not student_id or not school_year_id:
            return Response({"detail": _("student et school_year sont obligatoires")}, status=400)

        month_first = f"{d[:7]}-01"

        paid = CanteenSubscription.objects.filter(
            student_id=student_id,
            school_year_id=school_year_id,
            month=month_first,
            status="PAID",
        ).exists()

        if not paid:
            return Response({"detail": _("Forfait cantine non payé pour ce mois")}, status=403)

        obj, created = CanteenAttendance.objects.get_or_create(
            student_id=student_id,
            school_year_id=school_year_id,
            date=d,
            defaults={"status": "SERVED"},
        )

        if obj.status != "SERVED":
            obj.status = "SERVED"
            obj.save()

        return Response(
            {
                "served": True,
                "attendance_id": obj.id,
                "created": created
            },
            status=200
        )

    @extend_schema(
        parameters=[
            OpenApiParameter(name="classroom_id", type=OpenApiTypes.INT, required=True),
            OpenApiParameter(name="school_year_id", type=OpenApiTypes.INT, required=True),
            OpenApiParameter(name="month", type=OpenApiTypes.DATE, required=True),
        ]
    )
    @action(detail=False, methods=["get"], url_path="class-month-report")
    def class_month_report(self, request):
        """
        Rapport mensuel cantine par classe :
        - payé / non payé
        - nombre de jours servis
        """
        from students.models import Enrollment

        classroom_id = request.query_params.get("classroom_id")
        school_year_id = request.query_params.get("school_year_id")
        month = request.query_params.get("month")  # ex: 2026-02-01

        if not classroom_id or not school_year_id or not month:
            return Response({"detail": _("classroom_id, school_year_id, month sont obligatoires")}, status=400)

        enrollments = Enrollment.objects.filter(
            classroom_id=classroom_id,
            school_year_id=school_year_id,
            status="ENROLLED",
        ).select_related("student")

        student_ids = [e.student_id for e in enrollments]

        paid_students = set(
            CanteenSubscription.objects.filter(
                school_year_id=school_year_id,
                month=month,
                status="PAID",
                student_id__in=student_ids,
            ).values_list("student_id", flat=True)
        )

        served_counts = dict(
            CanteenAttendance.objects.filter(
                school_year_id=school_year_id,
                date__startswith=month[:7],  # "YYYY-MM"
                student_id__in=student_ids,
                status="SERVED",
            ).values("student_id").annotate(c=Count("id")).values_list("student_id", "c")
        )

        results = []
        for e in enrollments:
            s = e.student
            results.append({
                "student_id": s.id,
                "student_name": f"{s.first_name} {s.last_name}",
                "paid": s.id in paid_students,
                "served_days": served_counts.get(s.id, 0),
            })

        return Response({
            "classroom_id": int(classroom_id),
            "school_year_id": int(school_year_id),
            "month": month,
            "results": results,
        }, status=200)
