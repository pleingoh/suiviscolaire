from datetime import date as dt_date
from decimal import Decimal

from django.db.models import Sum
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.access import ensure_same_school, ensure_user_school, is_global_admin
from students.models import Enrollment

from .models import FeeInstallment, FeePlan, StudentFeeAccount
from .serializers import FeeInstallmentSerializer, FeePlanSerializer, StudentFeeAccountSerializer
from .services import create_installments


class SchoolScopedViewSetMixin:
    school_lookup = None

    def get_queryset(self):
        queryset = self.queryset.all()
        if is_global_admin(self.request.user):
            return queryset
        return queryset.filter(**{self.school_lookup: ensure_user_school(self.request.user)}).distinct()


class FeePlanViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = FeePlan.objects.all()
    serializer_class = FeePlanSerializer
    permission_classes = [IsAuthenticated]
    school_lookup = "school"

    def perform_create(self, serializer):
        ensure_same_school(self.request.user, serializer.validated_data["school"])
        ensure_same_school(self.request.user, serializer.validated_data["school_year"].school)
        serializer.save()


class StudentFeeAccountViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = StudentFeeAccount.objects.all()
    serializer_class = StudentFeeAccountSerializer
    permission_classes = [IsAuthenticated]
    school_lookup = "student__school"

    def perform_create(self, serializer):
        ensure_same_school(self.request.user, serializer.validated_data["student"].school)
        serializer.save()

    @action(detail=True, methods=["post"], url_path="generate-installments")
    def generate_installments(self, request, pk=None):
        account = self.get_object()
        FeeInstallment.objects.filter(account=account).delete()
        create_installments(account)
        return Response({"detail": "Echeances generees avec succes"}, status=200)

    @action(detail=True, methods=["get"], url_path="summary")
    def summary(self, request, pk=None):
        account = self.get_object()
        queryset = FeeInstallment.objects.filter(account=account).order_by("due_month")
        total_due = queryset.aggregate(x=Sum("amount_due"))["x"] or Decimal("0.00")
        total_paid = queryset.aggregate(x=Sum("amount_paid"))["x"] or Decimal("0.00")
        remaining = total_due - total_paid
        paid_count = queryset.filter(is_paid=True).count()
        unpaid_count = queryset.filter(is_paid=False).count()
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
                "installments": FeeInstallmentSerializer(queryset, many=True).data,
            },
            status=200,
        )


class FeeInstallmentViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = FeeInstallment.objects.all()
    serializer_class = FeeInstallmentSerializer
    permission_classes = [IsAuthenticated]
    school_lookup = "account__student__school"


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
        if not is_global_admin(request.user):
            enrollments = enrollments.filter(student__school=ensure_user_school(request.user))

        student_ids = [enrollment.student_id for enrollment in enrollments]
        plan = FeePlan.objects.filter(school_year_id=school_year_id, is_active=True).first()
        if not plan:
            return Response({"detail": "Aucun plan scolarite actif trouve"}, status=400)

        accounts = {
            account.student_id: account
            for account in StudentFeeAccount.objects.filter(
                school_year_id=school_year_id,
                student_id__in=student_ids,
            ).select_related("plan")
        }

        cutoff = as_of[:7] + "-01"
        results = []
        for enrollment in enrollments:
            student = enrollment.student
            account = accounts.get(student.id)
            if not account:
                results.append(
                    {
                        "student_id": student.id,
                        "student_name": f"{student.first_name} {student.last_name}",
                        "total_due": str(plan.total_amount),
                        "total_paid": "0.00",
                        "remaining": str(plan.total_amount),
                        "late_installments": plan.installments,
                        "status": "LATE",
                    }
                )
                continue

            queryset = FeeInstallment.objects.filter(account=account)
            total_due = queryset.aggregate(x=Sum("amount_due"))["x"] or Decimal("0.00")
            total_paid = queryset.aggregate(x=Sum("amount_paid"))["x"] or Decimal("0.00")
            remaining = total_due - total_paid
            late_installments = queryset.filter(due_month__lte=cutoff, is_paid=False).count()
            results.append(
                {
                    "student_id": student.id,
                    "student_name": f"{student.first_name} {student.last_name}",
                    "total_due": str(total_due),
                    "total_paid": str(total_paid),
                    "remaining": str(remaining),
                    "late_installments": late_installments,
                    "status": "OK" if late_installments == 0 else "LATE",
                }
            )

        return Response({"classroom_id": int(classroom_id), "school_year_id": int(school_year_id), "as_of": as_of, "results": results}, status=200)

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
            return Response({"detail": "Aucun plan scolarite actif trouve"}, status=400)

        account = StudentFeeAccount.objects.filter(student_id=student_id, school_year_id=school_year_id).select_related("plan").first()
        if account and not is_global_admin(request.user):
            ensure_same_school(request.user, account.student.school)

        if not account:
            return Response(
                {
                    "student_id": int(student_id),
                    "school_year_id": int(school_year_id),
                    "plan_total": str(plan.total_amount),
                    "total_due": str(plan.total_amount),
                    "total_paid": "0.00",
                    "remaining": str(plan.total_amount),
                    "credit_balance": "0.00",
                    "status": "LATE",
                },
                status=200,
            )

        queryset = FeeInstallment.objects.filter(account=account)
        total_due = queryset.aggregate(x=Sum("amount_due"))["x"] or Decimal("0.00")
        total_paid = queryset.aggregate(x=Sum("amount_paid"))["x"] or Decimal("0.00")
        remaining = total_due - total_paid
        return Response(
            {
                "student_id": int(student_id),
                "school_year_id": int(school_year_id),
                "account_id": account.id,
                "plan_total": str(account.plan.total_amount),
                "total_due": str(total_due),
                "total_paid": str(total_paid),
                "remaining": str(remaining),
                "credit_balance": str(account.credit_balance),
                "status": "OK" if remaining <= 0 else "LATE",
            },
            status=200,
        )
