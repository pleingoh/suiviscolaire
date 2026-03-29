from django.db import models


class School(models.Model):
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=50, unique=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=30, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Ecole"
        verbose_name_plural = "Ecoles"

    def __str__(self):
        return self.name


class SchoolYear(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="years")
    name = models.CharField(max_length=20)
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)

    class Meta:
        unique_together = ("school", "name")
        verbose_name = "Annee scolaire"
        verbose_name_plural = "Annees scolaires"

    def __str__(self):
        return f"{self.school.code} - {self.name}"


class Term(models.Model):
    school_year = models.ForeignKey(SchoolYear, on_delete=models.CASCADE, related_name="terms")
    name = models.CharField(max_length=20)
    start_date = models.DateField()
    end_date = models.DateField()

    class Meta:
        unique_together = ("school_year", "name")
        verbose_name = "Periode"
        verbose_name_plural = "Periodes"

    def __str__(self):
        return f"{self.school_year.name} - {self.name}"


class GradeLevel(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="grade_levels")
    name = models.CharField(max_length=50)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("school", "name")
        ordering = ["sort_order", "name"]
        verbose_name = "Niveau"
        verbose_name_plural = "Niveaux"

    def __str__(self):
        return self.name


class ClassRoom(models.Model):
    school_year = models.ForeignKey(SchoolYear, on_delete=models.CASCADE, related_name="classes")
    grade_level = models.ForeignKey(GradeLevel, on_delete=models.PROTECT, related_name="classes")
    name = models.CharField(max_length=60)
    capacity = models.PositiveIntegerField(blank=True, null=True)

    class Meta:
        unique_together = ("school_year", "name")
        verbose_name = "Classe"
        verbose_name_plural = "Classes"

    def __str__(self):
        return f"{self.name} ({self.school_year.name})"


class SchoolSetting(models.Model):
    school = models.OneToOneField(School, on_delete=models.CASCADE, related_name="settings")
    late_after_time = models.TimeField(default="07:30:00")
    notify_parents = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Parametre d'ecole"
        verbose_name_plural = "Parametres d'ecole"

    def __str__(self):
        return f"Parametres - {self.school.code}"
