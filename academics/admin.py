from django.contrib import admin
from core.admin_mixins import SchoolScopedAdminMixin
from .models import Subject, TeacherAssignment, Evaluation, Grade


@admin.register(Subject)
class SubjectAdmin(SchoolScopedAdminMixin):
    school_lookup = "school"
    list_display = ("id", "name")
    search_fields = ("name",)


@admin.register(TeacherAssignment)
class TeacherAssignmentAdmin(SchoolScopedAdminMixin):
    school_lookup = "class_room__school_year__school"
    list_display = ("id", "teacher", "subject", "class_room", "school_year")
    list_filter = ("school_year", "class_room", "subject")
    search_fields = ("subject__name",)


@admin.register(Evaluation)
class EvaluationAdmin(SchoolScopedAdminMixin):
    school_lookup = "class_room__school_year__school"
    list_display = ("id", "title", "eval_type", "subject", "class_room", "term", "date", "coefficient")
    list_filter = ("eval_type", "term", "class_room", "subject")
    search_fields = ("title", "subject__name")
    date_hierarchy = "date"


@admin.register(Grade)
class GradeAdmin(SchoolScopedAdminMixin):
    school_lookup = "student__school"
    list_display = ("id", "evaluation", "student", "score", "is_absent")
    list_filter = ("is_absent",)
    search_fields = ("evaluation__title",)
