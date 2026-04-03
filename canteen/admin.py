from django.contrib import admin
from core.admin_mixins import SchoolScopedAdminMixin
from .models import CanteenPlan, CanteenSubscription, CanteenAttendance


@admin.register(CanteenPlan)
class CanteenPlanAdmin(SchoolScopedAdminMixin):
    school_lookup = "school"
    list_display = ("id", "school", "monthly_price", "is_active")
    list_filter = ("is_active",)
    search_fields = ("school__name",)


@admin.register(CanteenSubscription)
class CanteenSubscriptionAdmin(SchoolScopedAdminMixin):
    school_lookup = "student__school"
    list_display = ("id", "student", "school_year", "month", "status", "amount", "paid_at")
    list_filter = ("status", "school_year", "month")
    search_fields = ("student__first_name", "student__last_name")
    date_hierarchy = "month"


@admin.register(CanteenAttendance)
class CanteenAttendanceAdmin(SchoolScopedAdminMixin):
    school_lookup = "student__school"
    list_display = ("id", "student", "date", "status")
    list_filter = ("status", "date")
    search_fields = ("student__first_name", "student__last_name")
    date_hierarchy = "date"
