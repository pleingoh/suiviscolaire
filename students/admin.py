from django.contrib import admin
from django.http import Http404, HttpResponse
from django.urls import path, reverse
from django.utils.html import format_html

from academics.models import Grade
from academics.pdf import build_bulletin_pdf
from core.models import Term

from .models import Enrollment, Student


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("id", "student", "classroom", "school_year", "status")
    list_filter = ("school_year", "status")
    search_fields = ("student__first_name", "student__last_name")


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("id", "first_name", "last_name", "bulletin_button")
    search_fields = ("first_name", "last_name", "matricule")

    def bulletin_button(self, obj):
        return format_html(
            '<a class="button" href="{}">Bulletin PDF</a>',
            reverse("admin:student-bulletin", args=[obj.id]),
        )

    bulletin_button.short_description = "Bulletin"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:student_id>/bulletin/",
                self.admin_site.admin_view(self.bulletin_pdf),
                name="student-bulletin",
            ),
        ]
        return custom_urls + urls

    def get_mention(self, avg):
        if avg >= 16:
            return "Tres bien"
        if avg >= 14:
            return "Bien"
        if avg >= 12:
            return "Assez bien"
        if avg >= 10:
            return "Passable"
        return "Insuffisant"

    def get_appreciation(self, avg):
        if avg >= 16:
            return "Excellent travail"
        if avg >= 14:
            return "Tres bon travail"
        if avg >= 12:
            return "Bon travail"
        if avg >= 10:
            return "Peut mieux faire"
        return "Travail insuffisant"

    def bulletin_pdf(self, request, student_id):
        try:
            student = Student.objects.get(pk=student_id)
        except Student.DoesNotExist as exc:
            raise Http404("Eleve introuvable") from exc

        term_id = request.GET.get("term_id")
        enrollment = (
            Enrollment.objects.filter(student_id=student_id)
            .select_related("school_year", "classroom")
            .order_by("-id")
            .first()
        )

        if not enrollment:
            return HttpResponse("Aucune inscription trouvee")

        if not term_id:
            terms = Term.objects.filter(school_year=enrollment.school_year).order_by("start_date")
            links = []
            for term in terms:
                url = reverse("admin:student-bulletin", args=[student.id]) + f"?term_id={term.id}"
                links.append(f'<li><a href="{url}">{term.name}</a></li>')
            html = f"""
            <h2>Choisir une periode</h2>
            <ul>
            {''.join(links)}
            </ul>
            """
            return HttpResponse(html)

        grades = Grade.objects.filter(
            student_id=student_id,
            evaluation__term_id=term_id,
        ).select_related("evaluation", "evaluation__subject")

        subjects_map = {}
        total_sum = 0
        total_coef = 0

        for grade in grades:
            subject = grade.evaluation.subject.name
            subjects_map.setdefault(subject, {"sum": 0, "coef": 0})

            if not grade.is_absent:
                coef = int(grade.evaluation.coefficient)
                score = float(grade.score)
                subjects_map[subject]["sum"] += score * coef
                subjects_map[subject]["coef"] += coef
                total_sum += score * coef
                total_coef += coef

        subjects = []
        for name, data in subjects_map.items():
            avg = data["sum"] / data["coef"] if data["coef"] else 0
            subjects.append({"subject": name, "average": round(avg, 2)})

        general_average = total_sum / total_coef if total_coef else 0

        classroom_id = enrollment.classroom_id
        class_students = Enrollment.objects.filter(classroom_id=classroom_id).values_list("student_id", flat=True)
        averages = []

        for sid in class_students:
            student_grades = Grade.objects.filter(student_id=sid, evaluation__term_id=term_id)
            current_sum = 0
            current_coef = 0

            for grade in student_grades:
                if not grade.is_absent:
                    coef = int(grade.evaluation.coefficient)
                    score = float(grade.score)
                    current_sum += score * coef
                    current_coef += coef

            averages.append((sid, current_sum / current_coef if current_coef else 0))

        averages.sort(key=lambda item: item[1], reverse=True)

        rank = 1
        for index, (sid, _) in enumerate(averages):
            if sid == student_id:
                rank = index + 1
                break

        term = Term.objects.filter(pk=term_id).select_related("school_year").first()
        payload = {
            "student_id": student.id,
            "term_id": int(term_id),
            "student_name": f"{student.first_name} {student.last_name}",
            "classroom_name": enrollment.classroom.name,
            "term_name": term.name,
            "school_year_name": term.school_year.name,
            "subjects": subjects,
            "general_average": round(general_average, 2),
            "rank": rank,
            "class_size": len(averages),
            "mention": self.get_mention(general_average),
            "appreciation": self.get_appreciation(general_average),
        }

        pdf = build_bulletin_pdf(payload)
        return HttpResponse(pdf, content_type="application/pdf")
