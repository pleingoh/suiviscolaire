from django.db import models

from accounts.models import User
from core.models import ClassRoom, School, SchoolYear, Term
from students.models import Student


class Subject(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="subjects")
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("school", "name")
        verbose_name = "Matiere"
        verbose_name_plural = "Matieres"

    def __str__(self):
        return self.name


class TeacherAssignment(models.Model):
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name="teaching_assignments")
    class_room = models.ForeignKey(ClassRoom, on_delete=models.CASCADE, related_name="teacher_assignments")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="teacher_assignments")
    school_year = models.ForeignKey(SchoolYear, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("teacher", "class_room", "subject", "school_year")
        verbose_name = "Affectation enseignant"
        verbose_name_plural = "Affectations enseignant"

    def __str__(self):
        return f"{self.teacher.full_name} - {self.class_room.name} - {self.subject.name}"


class Evaluation(models.Model):
    TYPE_CHOICES = [
        ("HOMEWORK", "Devoir"),
        ("QUIZ", "Interrogation"),
        ("EXAM", "Examen"),
    ]

    school_year = models.ForeignKey(SchoolYear, on_delete=models.CASCADE)
    term = models.ForeignKey(Term, on_delete=models.CASCADE)
    class_room = models.ForeignKey(ClassRoom, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    eval_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    title = models.CharField(max_length=150)
    date = models.DateField()
    coefficient = models.PositiveIntegerField(default=1)
    max_score = models.DecimalField(max_digits=6, decimal_places=2, default=20)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "Evaluation"
        verbose_name_plural = "Evaluations"

    def __str__(self):
        return f"{self.class_room.name} - {self.subject.name} - {self.title}"


class Grade(models.Model):
    evaluation = models.ForeignKey(Evaluation, on_delete=models.CASCADE, related_name="grades")
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="grades")
    score = models.DecimalField(max_digits=6, decimal_places=2)
    is_absent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("evaluation", "student")
        verbose_name = "Note"
        verbose_name_plural = "Notes"

    def __str__(self):
        return f"{self.student} - {self.evaluation} : {self.score}"
