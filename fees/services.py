from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from .models import StudentFeeAccount, FeeInstallment


def add_months(d: date, months: int) -> date:
    y = d.year + (d.month - 1 + months) // 12
    m = (d.month - 1 + months) % 12 + 1
    return date(y, m, 1)


def quantize_money(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def create_installments(account: StudentFeeAccount):
    plan = account.plan
    per = quantize_money(plan.total_amount / Decimal(plan.installments))

    for i in range(plan.installments):
        due = add_months(plan.start_month, i)
        FeeInstallment.objects.get_or_create(
            account=account,
            due_month=due,
            defaults={"amount_due": per},
        )
