from django.contrib.admin import AdminSite
from django.contrib import admin
from django.shortcuts import redirect
from accounts.forms import EmailOrPhoneAdminAuthenticationForm


class SchoolAdminSite(AdminSite):
    site_header = "Suivi scolaire"
    site_title = "Administration"
    index_title = "Tableau de bord"

    def index(self, request, extra_context=None):
        return redirect("/admin/dashboard/")


admin.site.login_form = EmailOrPhoneAdminAuthenticationForm
