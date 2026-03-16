from django.conf import settings
from django.db import models

from core.models import School, SchoolYear
from students.models import Student


class CashTransaction(models.Model):
    STATUS_CHOICES = (
        ("PENDING", "En attente"),
        ("VALIDATED", "Validee"),
        ("CANCELLED", "Annulee"),
    )

    TYPE_CHOICES = (
        ("IN", "Entree"),
        ("OUT", "Sortie"),
    )

    SERVICE_CHOICES = (
        ("SCOLARITE", "Scolarite"),
        ("CANTINE", "Cantine"),
        ("AUTRE", "Autre"),
    )

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="cash_transactions")
    school_year = models.ForeignKey(SchoolYear, on_delete=models.CASCADE, related_name="cash_transactions")
    student = models.ForeignKey(Student, null=True, blank=True, on_delete=models.SET_NULL, related_name="cash_transactions")
    transaction_type = models.CharField(max_length=3, choices=TYPE_CHOICES)
    service = models.CharField(max_length=15, choices=SERVICE_CHOICES, default="SCOLARITE")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=20, default="CASH")
    reference = models.CharField(max_length=100, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    canteen_month = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="PENDING")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="cash_tx_created")
    validated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="cash_tx_validated")
    created_at = models.DateTimeField(auto_now_add=True)
    validated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Transaction de caisse"
        verbose_name_plural = "Transactions de caisse"

    def __str__(self):
        return f"{self.transaction_type} {self.amount} {self.service} ({self.status})"

    def save(self, *args, **kwargs):
        if self.canteen_month:
            self.canteen_month = self.canteen_month.replace(day=1)
        super().save(*args, **kwargs)
