from decimal import Decimal

from django.utils import timezone
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import CashTransaction
from .serializers import CashTransactionSerializer

from canteen.models import CanteenSubscription, CanteenPlan

from fees.models import StudentFeeAccount, FeeInstallment, FeePlan
from fees.services import create_installments


class CashTransactionViewSet(viewsets.ModelViewSet):
    queryset = CashTransaction.objects.all().order_by("-created_at")
    serializer_class = CashTransactionSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["post"], url_path="validate")
    def validate_tx(self, request, pk=None):
        tx = self.get_object()

        # 1) si déjà validée, on renvoie direct
        if tx.status == "VALIDATED":
            return Response(CashTransactionSerializer(tx).data, status=200)

        # 2) on valide la transaction
        tx.status = "VALIDATED"
        tx.validated_by = request.user
        tx.validated_at = timezone.now()
        tx.save()

        # ----------------------------
        # ✅ CANTINE : crée/MAJ abonnement PAID
        # ----------------------------
        if tx.service == "CANTINE" and tx.transaction_type == "IN":
            if not tx.student_id or not tx.canteen_month:
                return Response({"detail": _("student et canteen_month requis pour cantine")}, status=400)

            month_first = tx.canteen_month.replace(day=1)

            plan = CanteenPlan.objects.filter(school=tx.school, is_active=True).first()
            if not plan:
                return Response({"detail": _("Aucun plan cantine actif trouvé")}, status=400)

            CanteenSubscription.objects.update_or_create(
                student_id=tx.student_id,
                school_year_id=tx.school_year_id,
                month=month_first,
                defaults={
                    "plan": plan,
                    "amount": tx.amount,
                    "status": "PAID",
                    "paid_at": timezone.now(),
                },
            )

        # ----------------------------
        # ✅ SCOLARITE : applique paiement sur échéances
        # ----------------------------
        if tx.service == "SCOLARITE" and tx.transaction_type == "IN":
            if not tx.student_id:
                return Response({"detail": _("student requis pour scolarité")}, status=400)

            plan = FeePlan.objects.filter(
                school=tx.school,
                school_year=tx.school_year,
                is_active=True
            ).first()

            if not plan:
                return Response({"detail": _("Aucun plan scolarité actif trouvé")}, status=400)

            account, _ = StudentFeeAccount.objects.get_or_create(
                student_id=tx.student_id,
                school_year=tx.school_year,
                defaults={"plan": plan},
            )

            # si l'account existe mais plan différent
            if account.plan_id != plan.id:
                account.plan = plan
                account.save()

            # créer échéances si pas encore créées
            if not FeeInstallment.objects.filter(account=account).exists():
                create_installments(account)

            remaining = Decimal(tx.amount)

            installments = FeeInstallment.objects.filter(account=account).order_by("due_month")
            for inst in installments:
                if remaining <= 0:
                    break
                if inst.is_paid:
                    continue

                need = inst.amount_due - inst.amount_paid
                if need <= 0:
                    continue

                applied = need if remaining >= need else remaining
                inst.amount_paid = inst.amount_paid + applied
                inst.save()

                remaining -= applied

        return Response(CashTransactionSerializer(tx).data, status=200)
        if remaining > 0:
            account.credit_balance = account.credit_balance + remaining
            account.save()

