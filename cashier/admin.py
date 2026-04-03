from django.contrib import admin

from core.admin_mixins import SchoolScopedAdminMixin

from .models import CashTransaction


@admin.register(CashTransaction)
class CashTransactionAdmin(SchoolScopedAdminMixin):
    school_lookup = "school"
    list_display = ("id", "school", "school_year", "student", "service", "transaction_type", "amount", "status", "created_at")
    list_filter = ("school", "school_year", "service", "transaction_type", "status")
    search_fields = ("student__first_name", "student__last_name", "reference")
