from django.contrib import admin

from .models import ClassRoom, GradeLevel, School, SchoolSetting, SchoolYear, Term


def _is_school_super_admin(user):
    if not user.is_authenticated or not user.is_active or not user.is_staff:
        return False
    if user.is_superuser:
        return True

    role_code = getattr(getattr(user, "role", None), "code", "") or ""
    normalized_role = role_code.strip().lower().replace("-", "_").replace(" ", "_")
    return normalized_role == "super_admin"


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "phone", "email", "is_active")
    list_display_links = ("name", "code")
    search_fields = ("name", "code", "phone", "email")
    list_filter = ("is_active",)
    ordering = ("name",)
    fields = ("name", "code", "address", "phone", "email", "is_active")

    def has_module_permission(self, request):
        return _is_school_super_admin(request.user)

    def has_view_permission(self, request, obj=None):
        return _is_school_super_admin(request.user)

    def has_add_permission(self, request):
        return _is_school_super_admin(request.user)

    def has_change_permission(self, request, obj=None):
        return _is_school_super_admin(request.user)

    def has_delete_permission(self, request, obj=None):
        return _is_school_super_admin(request.user)


admin.site.register(SchoolYear)
admin.site.register(Term)
admin.site.register(GradeLevel)
admin.site.register(ClassRoom)
admin.site.register(SchoolSetting)

