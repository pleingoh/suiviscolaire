from decimal import Decimal

from django.db import transaction
from django.http import HttpResponse
from django.utils import translation
from django.utils.translation import gettext as _

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from .models import Subject, TeacherAssignment, Evaluation, Grade
from .serializers import (
    SubjectSerializer,
    TeacherAssignmentSerializer,
    EvaluationSerializer,
    GradeSerializer,
)

from students.models import Enrollment, Student
from core.models import Term
from .pdf import build_bulletin_pdf


# =========================================================
# CRUD VIEWSETS
# =========================================================

class SubjectViewSet(viewsets.ModelViewSet):
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer
    permission_classes = [IsAuthenticated]


class TeacherAssignmentViewSet(viewsets.ModelViewSet):
    queryset = TeacherAssignment.objects.all()
    serializer_class = TeacherAssignmentSerializer
    permission_classes = [IsAuthenticated]


class GradeViewSet(viewsets.ModelViewSet):
    queryset = Grade.objects.all()
    serializer_class = GradeSerializer
    permission_classes = [IsAuthenticated]


class EvaluationViewSet(viewsets.ModelViewSet):
    queryset = Evaluation.objects.all()
    serializer_class = EvaluationSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["post"], url_path="bulk-grades")
    def bulk_grades(self, request, pk=None):
        evaluation = self.get_object()
        grades = request.data.get("grades", [])

        if not isinstance(grades, list) or not grades:
            return Response(
                {"detail": _("grades doit être une liste non vide")},
                status=400
            )

        created, updated = 0, 0

        with transaction.atomic():
            for item in grades:
                student_id = item.get("student")
                score = item.get("score")
                is_absent = bool(item.get("is_absent", False))

                if not student_id:
                    return Response(
                        {"detail": _("Chaque item doit contenir student")},
                        status=400
                    )

                obj, was_created = Grade.objects.update_or_create(
                    evaluation=evaluation,
                    student_id=student_id,
                    defaults={
                        "score": score if score is not None else 0,
                        "is_absent": is_absent,
                    },
                )

                if was_created:
                    created += 1
                else:
                    updated += 1

        return Response({
            "evaluation_id": evaluation.id,
            "created": created,
            "updated": updated
        })


# =========================================================
# BULLETIN JSON (ÉLÈVE)
# =========================================================

class BulletinAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter("student_id", OpenApiTypes.INT, required=True),
            OpenApiParameter("term_id", OpenApiTypes.INT, required=True),
        ]
    )
    def get(self, request):
        student_id = request.query_params.get("student_id")
        term_id = request.query_params.get("term_id")

        if not student_id or not term_id:
            return Response(
                {"detail": _("student_id et term_id sont obligatoires")},
                status=400
            )

        grades = Grade.objects.filter(
            student_id=student_id,
            evaluation__term_id=term_id,
        ).select_related("evaluation", "evaluation__subject")

        subjects = {}
        total_sum = Decimal("0")
        total_coef = Decimal("0")

        for g in grades:
            subject_name = g.evaluation.subject.name
            subjects.setdefault(subject_name, [])

            coef = Decimal(str(g.evaluation.coefficient))
            score = Decimal(str(g.score))

            if not g.is_absent:
                total_sum += score * coef
                total_coef += coef

            subjects[subject_name].append({
                "score": float(score),
                "coefficient": int(coef),
                "is_absent": g.is_absent,
            })

        subject_results = []
        for name, notes in subjects.items():
            s_sum = Decimal("0")
            s_coef = Decimal("0")

            for n in notes:
                if n["is_absent"]:
                    continue
                s_sum += Decimal(str(n["score"])) * Decimal(str(n["coefficient"]))
                s_coef += Decimal(str(n["coefficient"]))

            avg = (s_sum / s_coef) if s_coef > 0 else Decimal("0")

            subject_results.append({
                "subject": name,
                "average": float(avg),
                "notes": notes
            })

        general_average = (total_sum / total_coef) if total_coef > 0 else Decimal("0")

        return Response({
            "student_id": int(student_id),
            "term_id": int(term_id),
            "subjects": subject_results,
            "general_average": float(general_average),
        })


# =========================================================
# BULLETIN PDF
# =========================================================

class BulletinPDFAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter("student_id", OpenApiTypes.INT, required=True),
            OpenApiParameter("term_id", OpenApiTypes.INT, required=True),
            OpenApiParameter("lang", OpenApiTypes.STR, required=False),
        ]
    )
    def get(self, request):
        student_id = request.query_params.get("student_id")
        term_id = request.query_params.get("term_id")
        lang = request.query_params.get("lang")

        if not student_id or not term_id:
            return Response(
                {"detail": _("student_id et term_id sont obligatoires")},
                status=400
            )

        if lang in ("fr", "en"):
            translation.activate(lang)

        student = Student.objects.get(id=int(student_id))
        term = Term.objects.select_related("school_year").get(id=int(term_id))

        # On réutilise la logique de calcul
        grades = Grade.objects.filter(
            student_id=student_id,
            evaluation__term_id=term_id,
        ).select_related("evaluation", "evaluation__subject")

        subjects = {}
        total_sum = Decimal("0")
        total_coef = Decimal("0")

        for g in grades:
            subject_name = g.evaluation.subject.name
            subjects.setdefault(subject_name, [])

            coef = Decimal(str(g.evaluation.coefficient))
            score = Decimal(str(g.score))

            if not g.is_absent:
                total_sum += score * coef
                total_coef += coef

            subjects[subject_name].append({
                "subject": subject_name,
                "average": float(score),
            })

        general_average = (total_sum / total_coef) if total_coef > 0 else Decimal("0")

        payload = {
            "student_id": int(student_id),
            "term_id": int(term_id),
            "student_name": f"{student.first_name} {student.last_name}",
            "classroom_name": "-",  # on pourra améliorer après
            "term_name": term.name,
            "school_year_name": term.school_year.name,
            "subjects": [
                {"subject": k, "average": v[0]["average"]}
                for k, v in subjects.items()
            ],
            "general_average": float(general_average),
            "lang": lang or "fr",
        }

        pdf_bytes = build_bulletin_pdf(payload)

        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = "inline; filename=bulletin.pdf"
        return response
    

class ClassBulletinAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter("classroom_id", OpenApiTypes.INT, required=True),
            OpenApiParameter("term_id", OpenApiTypes.INT, required=True),
        ]
    )
    def get(self, request):
        classroom_id = request.query_params.get("classroom_id")
        term_id = request.query_params.get("term_id")

        if not classroom_id or not term_id:
            return Response(
                {"detail": _("classroom_id et term_id sont obligatoires")},
                status=400
            )

        # élèves inscrits dans la classe
        enrollments = Enrollment.objects.filter(
            classroom_id=classroom_id,
            status="ENROLLED",
        ).select_related("student")

        results = []
        for e in enrollments:
            grades = Grade.objects.filter(
                student_id=e.student.id,
                evaluation__term_id=term_id,
            ).select_related("evaluation", "evaluation__subject")

            subjects = {}
            total_sum = Decimal("0")
            total_coef = Decimal("0")

            for g in grades:
                subject_name = g.evaluation.subject.name
                subjects.setdefault(subject_name, [])

                coef = Decimal(str(g.evaluation.coefficient))
                score = Decimal(str(g.score))

                if not g.is_absent:
                    total_sum += score * coef
                    total_coef += coef

                subjects[subject_name].append({
                    "score": float(score),
                    "coefficient": int(coef),
                    "is_absent": bool(g.is_absent),
                })

            subject_results = []
            for name, notes in subjects.items():
                s_sum = Decimal("0")
                s_coef = Decimal("0")
                for n in notes:
                    if n["is_absent"]:
                        continue
                    s_sum += Decimal(str(n["score"])) * Decimal(str(n["coefficient"]))
                    s_coef += Decimal(str(n["coefficient"]))

                avg = (s_sum / s_coef) if s_coef > 0 else Decimal("0")
                subject_results.append({"subject": name, "average": float(avg)})

            general_average = (total_sum / total_coef) if total_coef > 0 else Decimal("0")

            results.append({
                "student_id": e.student.id,
                "student_name": f"{e.student.first_name} {e.student.last_name}",
                "general_average": float(general_average),
                "subjects": subject_results,
            })

        return Response({
            "classroom_id": int(classroom_id),
            "term_id": int(term_id),
            "results": results,
        })
