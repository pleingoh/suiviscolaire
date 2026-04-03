"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.i18n import set_language
from django.contrib import admin
from django.shortcuts import redirect
from django.urls import include, path
from django.views.generic import RedirectView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from django.conf import settings
from django.conf.urls.static import static

from core.admin_dashboard import (
    admin_dashboard,
    admin_school_delete,
    admin_school_edit,
    admin_school_list,
)
from core.admin_site import SchoolAdminSite
from core.dashboard_pdf import export_dashboard_pdf

admin_site = SchoolAdminSite(name="school_admin")

urlpatterns = [
    path("", lambda request: redirect(f"/{settings.LANGUAGE_CODE}/admin/login/")),
]

urlpatterns += i18n_patterns(
    path("i18n/", include("django.conf.urls.i18n")),
    path("admin/", RedirectView.as_view(pattern_name="admin-dashboard", permanent=False)),
    path("admin/home/", admin.site.admin_view(admin.site.index), name="admin-home"),
    path("admin/dashboard/", admin_dashboard, name="admin-dashboard"),
    path("admin/dashboard/pdf/", export_dashboard_pdf, name="dashboard_pdf"),
    path("admin/schools/", admin_school_list, name="admin-school-list"),
    path("admin/schools/<int:pk>/edit/", admin_school_edit, name="admin-school-edit"),
    path("admin/schools/<int:pk>/delete/", admin_school_delete, name="admin-school-delete"),
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/auth/", include("accounts.urls")),
    path("api/core/", include("core.urls")),
    path("api/students/", include("students.urls")),
    path("api/attendance/", include("attendance.urls")),
    path("api/academics/", include("academics.urls")),
    path("api/canteen/", include("canteen.urls")),
    path("api/cashier/", include("cashier.urls")),
    path("api/fees/", include("fees.urls")),
    path("set-language/", set_language, name="set_language"),
    path("", lambda request: redirect("admin:login")),
)

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
