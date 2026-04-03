from decimal import Decimal

from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from canteen.models import CanteenPlan, CanteenSubscription
from core.access import ensure_same_school, ensure_user_school, is_global_admin
from fees.models import FeeInstallment, FeePlan, StudentFeeAccount
from fees.services import create_installments

from .models import CashTransaction
from .serializers import CashTransactionSerializer


class CashTransactionViewSet(viewsets.ModelViewSet):
    queryset = CashTransaction.objects.all().order_by("-created_at")
    serializer_class = CashTransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = CashTransaction.objects.all().order_by("-created_at")
        if is_global_admin(self.request.user):
            return queryset
        return queryset.filter(school=ensure_user_school(self.request.user))

    def perform_create(self, serializer):
        school = serializer.validated_data["school"]
        ensure_same_school(self.request.user, school)
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["post"], url_path="validate")
    def validate_tx(self, request, pk=None):
        transaction = self.get_object()
        if transaction.status == "VALIDATED":
            return Response(CashTransactionSerializer(transaction).data, status=200)

        transaction.status = "VALIDATED"
        transaction.validated_by = request.user
        transaction.validated_at = timezone.now()
        transaction.save()

        if transaction.service == "CANTINE" and transaction.transaction_type == "IN":
            if not transaction.student_id or not transaction.canteen_month:
                return Response({"detail": _("student et canteen_month requis pour cantine")}, status=400)

            month_first = transaction.canteen_month.replace(day=1)
            plan = CanteenPlan.objects.filter(school=transaction.school, is_active=True).first()
            if not plan:
                return Response({"detail": _("Aucun plan cantine actif trouve")}, status=400)

            CanteenSubscription.objects.update_or_create(
                student_id=transaction.student_id,
                school_year_id=transaction.school_year_id,
                month=month_first,
                defaults={
                    "plan": plan,
                    "amount": transaction.amount,
                    "status": "PAID",
                    "paid_at": timezone.now(),
                },
            )

        if transaction.service == "SCOLARITE" and transaction.transaction_type == "IN":
            if not transaction.student_id:
                return Response({"detail": _("student requis pour scolarite")}, status=400)

            plan = FeePlan.objects.filter(school=transaction.school, school_year=transaction.school_year, is_active=True).first()
            if not plan:
                return Response({"detail": _("Aucun plan scolarite actif trouve")}, status=400)

            account, _ = StudentFeeAccount.objects.get_or_create(
                student_id=transaction.student_id,
                school_year=transaction.school_year,
                defaults={"plan": plan},
            )
            if account.plan_id != plan.id:
                account.plan = plan
                account.save()

            if not FeeInstallment.objects.filter(account=account).exists():
                create_installments(account)

            remaining = Decimal(transaction.amount)
            installments = FeeInstallment.objects.filter(account=account).order_by("due_month")
            for installment in installments:
                if remaining <= 0:
                    break
                if installment.is_paid:
                    continue
                need = installment.amount_due - installment.amount_paid
                if need <= 0:
                    continue
                applied = need if remaining >= need else remaining
                installment.amount_paid = installment.amount_paid + applied
                installment.save()
                remaining -= applied

            if remaining > 0:
                account.credit_balance = account.credit_balance + remaining
                account.save()

        return Response(CashTransactionSerializer(transaction).data, status=200)
