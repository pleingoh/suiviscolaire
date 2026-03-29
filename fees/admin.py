from django.contrib import admin
from .models import FeePlan, StudentFeeAccount, FeeInstallment


@admin.register(FeePlan)
class FeePlanAdmin(admin.ModelAdmin):
    list_display = ("id", "school", "school_year", "total_amount", "is_active")
    list_filter = ("school_year", "is_active")
    search_fields = ("school__name",)


@admin.register(StudentFeeAccount)
class StudentFeeAccountAdmin(admin.ModelAdmin):
    list_display = ("id", "student", "school_year", "plan")
    list_filter = ("school_year",)
    search_fields = ("student__first_name", "student__last_name")


@admin.register(FeeInstallment)
class FeeInstallmentAdmin(admin.ModelAdmin):
    list_display = ("id", "account", "due_month", "amount_due", "amount_paid", "is_paid")
    list_filter = ("is_paid", "due_month")
    search_fields = ("account__student__first_name", "account__student__last_name")