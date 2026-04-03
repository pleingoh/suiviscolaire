from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated

from .access import ensure_same_school, ensure_user_school, is_global_admin
from .models import ClassRoom, GradeLevel, School, SchoolYear, Term
from .serializers import ClassRoomSerializer, GradeLevelSerializer, SchoolSerializer, SchoolYearSerializer, TermSerializer


class SchoolScopedViewSetMixin:
    school_lookup = None

    def get_queryset(self):
        queryset = self.queryset.all()
        if is_global_admin(self.request.user):
            return queryset
        school = ensure_user_school(self.request.user)
        if not self.school_lookup:
            return queryset.none()
        return queryset.filter(**{self.school_lookup: school}).distinct()


class SchoolViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = School.objects.all()
    serializer_class = SchoolSerializer
    permission_classes = [IsAuthenticated]
    school_lookup = "id"

    def perform_create(self, serializer):
        if not is_global_admin(self.request.user):
            raise PermissionDenied("Seul l'admin global peut creer une ecole.")
        serializer.save()

    def perform_update(self, serializer):
        school = serializer.instance
        ensure_same_school(self.request.user, school)
        serializer.save()


class SchoolYearViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = SchoolYear.objects.all()
    serializer_class = SchoolYearSerializer
    permission_classes = [IsAuthenticated]
    school_lookup = "school"

    def perform_create(self, serializer):
        ensure_same_school(self.request.user, serializer.validated_data["school"])
        serializer.save()


class TermViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = Term.objects.all()
    serializer_class = TermSerializer
    permission_classes = [IsAuthenticated]
    school_lookup = "school_year__school"

    def perform_create(self, serializer):
        ensure_same_school(self.request.user, serializer.validated_data["school_year"].school)
        serializer.save()


class GradeLevelViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = GradeLevel.objects.all()
    serializer_class = GradeLevelSerializer
    permission_classes = [IsAuthenticated]
    school_lookup = "school"

    def perform_create(self, serializer):
        ensure_same_school(self.request.user, serializer.validated_data["school"])
        serializer.save()


class ClassRoomViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = ClassRoom.objects.all()
    serializer_class = ClassRoomSerializer
    permission_classes = [IsAuthenticated]
    school_lookup = "school_year__school"

    def perform_create(self, serializer):
        ensure_same_school(self.request.user, serializer.validated_data["school_year"].school)
        serializer.save()
