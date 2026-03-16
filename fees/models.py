from decimal import Decimal

from django.db import models

from core.models import School, SchoolYear
from students.models import Student


class FeePlan(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="fee_plans")
    school_year = models.ForeignKey(SchoolYear, on_delete=models.CASCADE, related_name="fee_plans")
    name = models.CharField(max_length=100, default="Scolarite")
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    installments = models.PositiveIntegerField(default=10)
    start_month = models.DateField(help_text="1er jour du mois de debut (ex: 2026-09-01)")
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Plan de frais"
        verbose_name_plural = "Plans de frais"

    def save(self, *args, **kwargs):
        if self.start_month:
            self.start_month = self.start_month.replace(day=1)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.school} {self.school_year} - {self.total_amount}"


class StudentFeeAccount(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="fee_accounts")
    school_year = models.ForeignKey(SchoolYear, on_delete=models.CASCADE, related_name="fee_accounts")
    plan = models.ForeignKey(FeePlan, on_delete=models.PROTECT, related_name="student_accounts")
    created_at = models.DateTimeField(auto_now_add=True)
    credit_balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        unique_together = ("student", "school_year")
        verbose_name = "Compte de frais eleve"
        verbose_name_plural = "Comptes de frais eleve"

    def __str__(self):
        return f"{self.student} - {self.school_year}"


class FeeInstallment(models.Model):
    account = models.ForeignKey(StudentFeeAccount, on_delete=models.CASCADE, related_name="installments")
    due_month = models.DateField(help_text="1er jour du mois (ex: 2026-09-01)")
    amount_due = models.DecimalField(max_digits=12, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    is_paid = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("account", "due_month")
        ordering = ["due_month"]
        verbose_name = "Echeance"
        verbose_name_plural = "Echeances"

    def save(self, *args, **kwargs):
        if self.due_month:
            self.due_month = self.due_month.replace(day=1)
        self.is_paid = self.amount_paid >= self.amount_due
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.account} - {self.due_month} ({self.amount_paid}/{self.amount_due})"
