from django.db import models

from core.models import SchoolYear
from students.models import Student


class CanteenPlan(models.Model):
    school = models.ForeignKey("core.School", on_delete=models.CASCADE, related_name="canteen_plans")
    name = models.CharField(max_length=100, default="Forfait mensuel")
    monthly_price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Forfait cantine"
        verbose_name_plural = "Forfaits cantine"

    def __str__(self):
        return f"{self.school} - {self.name} ({self.monthly_price})"


class CanteenSubscription(models.Model):
    STATUS_CHOICES = (
        ("PENDING", "En attente"),
        ("PAID", "Paye"),
        ("CANCELLED", "Annule"),
    )

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="canteen_subscriptions")
    school_year = models.ForeignKey(SchoolYear, on_delete=models.CASCADE, related_name="canteen_subscriptions")
    month = models.DateField(help_text="Mettre le 1er jour du mois (ex: 2026-02-01)")
    plan = models.ForeignKey(CanteenPlan, on_delete=models.PROTECT, related_name="subscriptions")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="PENDING")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("student", "school_year", "month")
        verbose_name = "Abonnement cantine"
        verbose_name_plural = "Abonnements cantine"

    def __str__(self):
        return f"{self.student} - {self.month} - {self.status}"


class CanteenAttendance(models.Model):
    STATUS_CHOICES = (
        ("SERVED", "Servi"),
        ("NOT_SERVED", "Non servi"),
    )

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="canteen_attendance")
    school_year = models.ForeignKey(SchoolYear, on_delete=models.CASCADE, related_name="canteen_attendance")
    date = models.DateField()
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="SERVED")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("student", "school_year", "date")
        verbose_name = "Passage cantine"
        verbose_name_plural = "Passages cantine"
