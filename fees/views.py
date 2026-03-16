from datetime import date as dt_date
from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from .models import FeePlan, StudentFeeAccount, FeeInstallment
from .serializers import (
    FeePlanSerializer,
    StudentFeeAccountSerializer,
    FeeInstallmentSerializer,
)


# ---------------------------
# 1) FeePlan
# ---------------------------
class FeePlanViewSet(viewsets.ModelViewSet):
    queryset = FeePlan.objects.all()
    serializer_class = FeePlanSerializer
    permission_classes = [IsAuthenticated]


# ---------------------------
# 2) StudentFeeAccount
# ---------------------------
class StudentFeeAccountViewSet(viewsets.ModelViewSet):
    queryset = StudentFeeAccount.objects.all()
    serializer_class = StudentFeeAccountSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=["post"], url_path="generate-installments")
    def generate_installments(self, request, pk=None):
        """
        Génère les échéances mensuelles pour un compte (installments).
        """
        account = self.get_object()

        # éviter doublons
        FeeInstallment.objects.filter(account=account).delete()

        create_installments(account)
        return Response({"detail": "Echéances générées avec succès"}, status=200)

    @action(detail=True, methods=["get"], url_path="summary")
    def summary(self, request, pk=None):
        """
        Résumé scolarité d’un élève :
        total dû, total payé, reste, échéances payées / impayées.
        """
        account = self.get_object()

        qs = FeeInstallment.objects.filter(account=account).order_by("due_month")

        total_due = qs.aggregate(x=Sum("amount_due"))["x"] or Decimal("0.00")
        total_paid = qs.aggregate(x=Sum("amount_paid"))["x"] or Decimal("0.00")
        remaining = total_due - total_paid

        paid_count = qs.filter(is_paid=True).count()
        unpaid_count = qs.filter(is_paid=False).count()

        return Response(
            {
                "account_id": account.id,
                "student_id": account.student_id,
                "school_year_id": account.school_year_id,
                "plan_id": account.plan_id,
                "total_due": str(total_due),
                "total_paid": str(total_paid),
                "remaining": str(remaining),
                "paid_installments": paid_count,
                "unpaid_installments": unpaid_count,
                "installments": FeeInstallmentSerializer(qs, many=True).data,
            },
            status=200,
        )


# ---------------------------
# 3) FeeInstallment
# ---------------------------
class FeeInstallmentViewSet(viewsets.ModelViewSet):
    queryset = FeeInstallment.objects.all()
    serializer_class = FeeInstallmentSerializer
    permission_classes = [IsAuthenticated]


# ---------------------------
# 4) REPORTS
# ---------------------------
class FeeReportViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter(name="classroom_id", type=OpenApiTypes.INT, required=True),
            OpenApiParameter(name="school_year_id", type=OpenApiTypes.INT, required=True),
            OpenApiParameter(name="as_of", type=OpenApiTypes.DATE, required=False),
        ]
    )
    @action(detail=False, methods=["get"], url_path="class-status")
    def class_status(self, request):
        """
        Liste élèves d’une classe + statut scolarité.
        """
        from students.models import Enrollment

        classroom_id = request.query_params.get("classroom_id")
        school_year_id = request.query_params.get("school_year_id")
        as_of = request.query_params.get("as_of") or dt_date.today().isoformat()

        if not classroom_id or not school_year_id:
            return Response({"detail": "classroom_id et school_year_id sont obligatoires"}, status=400)

        enrollments = Enrollment.objects.filter(
            classroom_id=classroom_id,
            school_year_id=school_year_id,
            status="ENROLLED",
        ).select_related("student")

        student_ids = [e.student_id for e in enrollments]

        plan = FeePlan.objects.filter(
            school_year_id=school_year_id,
            is_active=True
        ).first()

        if not plan:
            return Response({"detail": "Aucun plan scolarité actif trouvé"}, status=400)

        accounts = {
            a.student_id: a
            for a in StudentFeeAccount.objects.filter(
                school_year_id=school_year_id,
                student_id__in=student_ids,
            ).select_related("plan")
        }

        results = []

        cutoff = as_of[:7] + "-01"

        for e in enrollments:
            s = e.student
            acc = accounts.get(s.id)

            # Pas encore de compte → considéré en retard
            if not acc:
                results.append({
                    "student_id": s.id,
                    "student_name": f"{s.first_name} {s.last_name}",
                    "total_due": str(plan.total_amount),
                    "total_paid": "0.00",
                    "remaining": str(plan.total_amount),
                    "late_installments": plan.installments,
                    "status": "LATE",
                })
                continue

            qs = FeeInstallment.objects.filter(account=acc)

            total_due = qs.aggregate(x=Sum("amount_due"))["x"] or Decimal("0.00")
            total_paid = qs.aggregate(x=Sum("amount_paid"))["x"] or Decimal("0.00")
            remaining = total_due - total_paid

            late_installments = qs.filter(due_month__lte=cutoff, is_paid=False).count()

            results.append({
                "student_id": s.id,
                "student_name": f"{s.first_name} {s.last_name}",
                "total_due": str(total_due),
                "total_paid": str(total_paid),
                "remaining": str(remaining),
                "late_installments": late_installments,
                "status": "OK" if late_installments == 0 else "LATE",
            })

        return Response(
            {
                "classroom_id": int(classroom_id),
                "school_year_id": int(school_year_id),
                "as_of": as_of,
                "results": results,
            },
            status=200,
        )
    
    @extend_schema(
    parameters=[
        OpenApiParameter(name="student_id", type=OpenApiTypes.INT, required=True),
        OpenApiParameter(name="school_year_id", type=OpenApiTypes.INT, required=True),
    ]
)
    @action(detail=False, methods=["get"], url_path="student-summary")
    def student_summary(self, request):
        student_id = request.query_params.get("student_id")
        school_year_id = request.query_params.get("school_year_id")

        if not student_id or not school_year_id:
            return Response({"detail": "student_id et school_year_id sont obligatoires"}, status=400)

        plan = FeePlan.objects.filter(school_year_id=school_year_id, is_active=True).first()
        if not plan:
            return Response({"detail": "Aucun plan scolarité actif trouvé"}, status=400)

        account = StudentFeeAccount.objects.filter(
            student_id=student_id,
            school_year_id=school_year_id
        ).select_related("plan").first()

        if not account:
            # pas de compte => rien payé
            return Response({
                "student_id": int(student_id),
                "school_year_id": int(school_year_id),
                "plan_total": str(plan.total_amount),
                "total_due": str(plan.total_amount),
                "total_paid": "0.00",
                "remaining": str(plan.total_amount),
                "credit_balance": "0.00",
                "status": "LATE",
            }, status=200)

        qs = FeeInstallment.objects.filter(account=account)
        total_due = qs.aggregate(x=Sum("amount_due"))["x"] or Decimal("0.00")
        total_paid = qs.aggregate(x=Sum("amount_paid"))["x"] or Decimal("0.00")
        remaining = total_due - total_paid

        return Response({
            "student_id": int(student_id),
            "school_year_id": int(school_year_id),
            "account_id": account.id,
            "plan_total": str(account.plan.total_amount),
            "total_due": str(total_due),
            "total_paid": str(total_paid),
            "remaining": str(remaining),
            "credit_balance": str(account.credit_balance),
            "status": "OK" if remaining <= 0 else "LATE",
        }, status=200)

