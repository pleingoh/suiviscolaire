from django.db import models

from core.models import SchoolYear
from students.models import Student


class Attendance(models.Model):
    STATUS_CHOICES = [
        ("PRESENT", "Present"),
        ("LATE", "En retard"),
        ("ABSENT", "Absent"),
        ("EARLY_LEAVE", "Sortie anticipee"),
    ]

    METHOD_CHOICES = [
        ("MANUAL", "Manuel"),
        ("FACIAL", "Reconnaissance faciale"),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="attendance_records")
    school_year = models.ForeignKey(SchoolYear, on_delete=models.CASCADE)
    date = models.DateField()
    arrival_time = models.TimeField(blank=True, null=True)
    departure_time = models.TimeField(blank=True, null=True)
    arrival_method = models.CharField(max_length=10, choices=METHOD_CHOICES, default="MANUAL")
    departure_method = models.CharField(max_length=10, choices=METHOD_CHOICES, default="MANUAL")
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="PRESENT")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("student", "school_year", "date")
        verbose_name = "Presence"
        verbose_name_plural = "Presences"

    def __str__(self):
        return f"{self.student} - {self.date}"
