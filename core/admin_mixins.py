from django.contrib import admin

from .access import is_global_admin


class SchoolScopedAdminMixin(admin.ModelAdmin):
    school_lookup = None

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if is_global_admin(request.user):
            return queryset
        if not request.user.school_id or not self.school_lookup:
            return queryset.none()
        return queryset.filter(**{self.school_lookup: request.user.school}).distinct()
