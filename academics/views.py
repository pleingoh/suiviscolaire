from decimal import Decimal

from django.db import transaction
from django.http import HttpResponse
from django.utils import translation
from django.utils.translation import gettext as _
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.access import ensure_same_school, ensure_user_school, is_global_admin
from core.models import Term
from students.models import Enrollment, Student

from .models import Evaluation, Grade, Subject, TeacherAssignment
from .pdf import build_bulletin_pdf
from .serializers import EvaluationSerializer, GradeSerializer, SubjectSerializer, TeacherAssignmentSerializer


class SchoolScopedViewSetMixin:
    school_lookup = None

    def get_queryset(self):
        queryset = self.queryset.all()
        if is_global_admin(self.request.user):
            return queryset
        school = ensure_user_school(self.request.user)
        return queryset.filter(**{self.school_lookup: school}).distinct()


class SubjectViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer
    permission_classes = [IsAuthenticated]
    school_lookup = "school"

    def perform_create(self, serializer):
        ensure_same_school(self.request.user, serializer.validated_data["school"])
        serializer.save()


class TeacherAssignmentViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = TeacherAssignment.objects.all()
    serializer_class = TeacherAssignmentSerializer
    permission_classes = [IsAuthenticated]
    school_lookup = "class_room__school_year__school"

    def perform_create(self, serializer):
        ensure_same_school(self.request.user, serializer.validated_data["class_room"].school_year.school)
        ensure_same_school(self.request.user, serializer.validated_data["subject"].school)
        serializer.save()


class GradeViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = Grade.objects.all()
    serializer_class = GradeSerializer
    permission_classes = [IsAuthenticated]
    school_lookup = "student__school"

    def perform_create(self, serializer):
        ensure_same_school(self.request.user, serializer.validated_data["student"].school)
        serializer.save()


class EvaluationViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = Evaluation.objects.all()
    serializer_class = EvaluationSerializer
    permission_classes = [IsAuthenticated]
    school_lookup = "class_room__school_year__school"

    def perform_create(self, serializer):
        ensure_same_school(self.request.user, serializer.validated_data["class_room"].school_year.school)
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["post"], url_path="bulk-grades")
    def bulk_grades(self, request, pk=None):
        evaluation = self.get_object()
        grades = request.data.get("grades", [])

        if not isinstance(grades, list) or not grades:
            return Response({"detail": _("grades doit etre une liste non vide")}, status=400)

        created = 0
        updated = 0
        with transaction.atomic():
            for item in grades:
                student_id = item.get("student")
                score = item.get("score")
                is_absent = bool(item.get("is_absent", False))
                if not student_id:
                    return Response({"detail": _("Chaque item doit contenir student")}, status=400)

                student = Student.objects.get(id=student_id)
                ensure_same_school(request.user, student.school)
                _, was_created = Grade.objects.update_or_create(
                    evaluation=evaluation,
                    student_id=student_id,
                    defaults={"score": score if score is not None else 0, "is_absent": is_absent},
                )
                created += int(was_created)
                updated += int(not was_created)

        return Response({"evaluation_id": evaluation.id, "created": created, "updated": updated})


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
            return Response({"detail": _("student_id et term_id sont obligatoires")}, status=400)

        student = Student.objects.select_related("school").get(id=int(student_id))
        ensure_same_school(request.user, student.school)
        grades = Grade.objects.filter(student_id=student_id, evaluation__term_id=term_id).select_related("evaluation", "evaluation__subject")

        subjects = {}
        total_sum = Decimal("0")
        total_coef = Decimal("0")
        for grade in grades:
            subject_name = grade.evaluation.subject.name
            subjects.setdefault(subject_name, [])
            coefficient = Decimal(str(grade.evaluation.coefficient))
            score = Decimal(str(grade.score))
            if not grade.is_absent:
                total_sum += score * coefficient
                total_coef += coefficient
            subjects[subject_name].append({"score": float(score), "coefficient": int(coefficient), "is_absent": grade.is_absent})

        results = []
        for name, notes in subjects.items():
            current_sum = Decimal("0")
            current_coef = Decimal("0")
            for note in notes:
                if note["is_absent"]:
                    continue
                current_sum += Decimal(str(note["score"])) * Decimal(str(note["coefficient"]))
                current_coef += Decimal(str(note["coefficient"]))
            average = current_sum / current_coef if current_coef > 0 else Decimal("0")
            results.append({"subject": name, "average": float(average), "notes": notes})

        general_average = total_sum / total_coef if total_coef > 0 else Decimal("0")
        return Response({"student_id": int(student_id), "term_id": int(term_id), "subjects": results, "general_average": float(general_average)})


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
            return Response({"detail": _("student_id et term_id sont obligatoires")}, status=400)

        if lang in ("fr", "en"):
            translation.activate(lang)

        student = Student.objects.select_related("school").get(id=int(student_id))
        ensure_same_school(request.user, student.school)
        term = Term.objects.select_related("school_year").get(id=int(term_id))
        grades = Grade.objects.filter(student_id=student_id, evaluation__term_id=term_id).select_related("evaluation", "evaluation__subject")

        subjects = {}
        total_sum = Decimal("0")
        total_coef = Decimal("0")
        for grade in grades:
            subject_name = grade.evaluation.subject.name
            subjects.setdefault(subject_name, [])
            coefficient = Decimal(str(grade.evaluation.coefficient))
            score = Decimal(str(grade.score))
            if not grade.is_absent:
                total_sum += score * coefficient
                total_coef += coefficient
            subjects[subject_name].append({"subject": subject_name, "average": float(score)})

        payload = {
            "student_id": int(student_id),
            "term_id": int(term_id),
            "student_name": f"{student.first_name} {student.last_name}",
            "classroom_name": "-",
            "term_name": term.name,
            "school_year_name": term.school_year.name,
            "subjects": [{"subject": name, "average": values[0]["average"]} for name, values in subjects.items()],
            "general_average": float(total_sum / total_coef if total_coef > 0 else Decimal("0")),
            "lang": lang or "fr",
        }
        response = HttpResponse(build_bulletin_pdf(payload), content_type="application/pdf")
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
            return Response({"detail": _("classroom_id et term_id sont obligatoires")}, status=400)

        enrollments = Enrollment.objects.filter(classroom_id=classroom_id, status="ENROLLED").select_related("student")
        if not is_global_admin(request.user):
            enrollments = enrollments.filter(student__school=ensure_user_school(request.user))

        results = []
        for enrollment in enrollments:
            grades = Grade.objects.filter(student_id=enrollment.student.id, evaluation__term_id=term_id).select_related("evaluation", "evaluation__subject")
            subjects = {}
            total_sum = Decimal("0")
            total_coef = Decimal("0")

            for grade in grades:
                subject_name = grade.evaluation.subject.name
                subjects.setdefault(subject_name, [])
                coefficient = Decimal(str(grade.evaluation.coefficient))
                score = Decimal(str(grade.score))
                if not grade.is_absent:
                    total_sum += score * coefficient
                    total_coef += coefficient
                subjects[subject_name].append({"score": float(score), "coefficient": int(coefficient), "is_absent": bool(grade.is_absent)})

            subject_results = []
            for name, notes in subjects.items():
                current_sum = Decimal("0")
                current_coef = Decimal("0")
                for note in notes:
                    if note["is_absent"]:
                        continue
                    current_sum += Decimal(str(note["score"])) * Decimal(str(note["coefficient"]))
                    current_coef += Decimal(str(note["coefficient"]))
                average = current_sum / current_coef if current_coef > 0 else Decimal("0")
                subject_results.append({"subject": name, "average": float(average)})

            results.append(
                {
                    "student_id": enrollment.student.id,
                    "student_name": f"{enrollment.student.first_name} {enrollment.student.last_name}",
                    "general_average": float(total_sum / total_coef if total_coef > 0 else Decimal("0")),
                    "subjects": subject_results,
                }
            )

        return Response({"classroom_id": int(classroom_id), "term_id": int(term_id), "results": results})
