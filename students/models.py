from django.db import models

from accounts.models import User
from core.models import ClassRoom, School, SchoolYear


class Student(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="students")
    matricule = models.CharField(max_length=50, unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    gender = models.CharField(max_length=1, choices=[("M", "Masculin"), ("F", "Feminin")])
    birth_date = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Eleve"
        verbose_name_plural = "Eleves"

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Enrollment(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="enrollments")
    school_year = models.ForeignKey(SchoolYear, on_delete=models.CASCADE)
    classroom = models.ForeignKey(ClassRoom, on_delete=models.CASCADE)
    enrolled_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ("ENROLLED", "Inscrit"),
            ("TRANSFERRED", "Transfere"),
            ("DROPPED", "Abandonne"),
        ],
        default="ENROLLED",
    )

    class Meta:
        unique_together = ("student", "school_year")
        verbose_name = "Inscription"
        verbose_name_plural = "Inscriptions"

    def __str__(self):
        return f"{self.student} - {self.school_year.name}"


class StudentParent(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="parents")
    parent = models.ForeignKey(User, on_delete=models.CASCADE, related_name="children")
    relationship = models.CharField(
        max_length=20,
        choices=[
            ("FATHER", "Pere"),
            ("MOTHER", "Mere"),
            ("GUARDIAN", "Tuteur"),
        ],
    )
    is_primary = models.BooleanField(default=False)

    class Meta:
        unique_together = ("student", "parent")
        verbose_name = "Responsable d'eleve"
        verbose_name_plural = "Responsables d'eleve"

    def __str__(self):
        return f"{self.parent.full_name} -> {self.student}"
