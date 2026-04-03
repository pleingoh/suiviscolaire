from unittest.mock import patch

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory, TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import Role
from core.admin import SchoolAdmin, SchoolAdminForm
from core.models import School


class AdminSchoolManagementTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            phone="770000000",
            password="testpass123",
            full_name="Super Admin",
        )
        self.client.force_login(self.user)
        self.school = School.objects.create(
            name="Ecole Alpha",
            code="ALPHA",
            address="Adresse",
            phone="77001122",
            email="alpha@example.com",
        )

    def test_school_list_page_is_available_for_super_admin(self):
        response = self.client.get(reverse("admin-school-list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ecole Alpha")

    def test_super_admin_can_edit_school(self):
        response = self.client.post(
            reverse("admin-school-edit", args=[self.school.pk]),
            {
                "name": "Ecole Beta",
                "code": "ALPHA",
                "address": "Nouvelle adresse",
                "phone": "77998877",
                "email": "beta@example.com",
                "is_active": "on",
            },
        )

        self.assertRedirects(response, reverse("admin-school-list"))
        self.school.refresh_from_db()
        self.assertEqual(self.school.name, "Ecole Beta")
        self.assertEqual(self.school.address, "Nouvelle adresse")

    def test_super_admin_can_delete_school(self):
        response = self.client.post(reverse("admin-school-delete", args=[self.school.pk]))

        self.assertRedirects(response, reverse("admin-school-list"))
        self.assertFalse(School.objects.filter(pk=self.school.pk).exists())

    def test_role_super_admin_can_access_django_admin_school_change(self):
        role = Role.objects.create(code="super_admin", label="Super Admin")
        user = get_user_model().objects.create_user(
            phone="771111111",
            password="testpass123",
            full_name="Role Super Admin",
            role=role,
            is_staff=True,
            is_active=True,
        )
        self.client.force_login(user)

        response = self.client.get(reverse("admin:core_school_change", args=[self.school.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ecole Alpha")


class SchoolAdminAccountTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.site = AdminSite()
        self.model_admin = SchoolAdmin(School, self.site)
        self.superuser = get_user_model().objects.create_superuser(
            phone="770000001",
            password="testpass123",
            full_name="Global Admin",
            email="global@example.com",
        )

    def _build_request(self, path):
        request = self.factory.post(path)
        request.user = self.superuser
        middleware = SessionMiddleware(lambda req: None)
        middleware.process_request(request)
        request.session.save()
        setattr(request, "_messages", FallbackStorage(request))
        return request

    def test_school_admin_form_prefills_existing_school_admin(self):
        school = School.objects.create(name="Ecole A", code="EA")
        school_admin = get_user_model().objects.create_user(
            phone="770000002",
            password="testpass123",
            full_name="Admin A",
            email="admina@example.com",
            school=school,
            is_staff=True,
        )

        form = SchoolAdminForm(instance=school)

        self.assertEqual(form.fields["admin_full_name"].initial, school_admin.full_name)
        self.assertEqual(form.fields["admin_phone"].initial, school_admin.phone)
        self.assertEqual(form.fields["admin_email"].initial, school_admin.email)

    @patch("core.admin.send_school_admin_welcome_email")
    def test_save_model_creates_school_admin_when_missing(self, send_email_mock):
        school = School(name="Ecole B", code="EB")
        form = SchoolAdminForm(
            data={
                "name": "Ecole B",
                "code": "EB",
                "address": "",
                "phone": "",
                "email": "ecoleb@example.com",
                "is_active": True,
                "admin_full_name": "Admin B",
                "admin_phone": "770000003",
                "admin_email": "adminb@example.com",
            },
            instance=school,
        )
        self.assertTrue(form.is_valid(), form.errors)
        request = self._build_request("/admin/core/school/add/")

        with self.captureOnCommitCallbacks(execute=True):
            self.model_admin.save_model(request, school, form, change=False)

        school_admin = get_user_model().objects.get(phone="770000003")
        self.assertEqual(school_admin.school, school)
        self.assertTrue(school_admin.is_staff)
        send_email_mock.assert_called_once()

    def test_school_admin_form_rejects_duplicate_admin_email_and_phone(self):
        get_user_model().objects.create_user(
            phone="770099999",
            password="testpass123",
            full_name="Utilisateur Existant",
            email="existing@example.com",
            is_staff=True,
        )
        form = SchoolAdminForm(
            data={
                "name": "Ecole D",
                "code": "ED",
                "address": "",
                "phone": "",
                "email": "ecoled@example.com",
                "is_active": True,
                "admin_full_name": "Admin D",
                "admin_phone": "770099999",
                "admin_email": "existing@example.com",
            },
            instance=School(name="Ecole D", code="ED"),
        )

        self.assertFalse(form.is_valid())
        self.assertIn("admin_phone", form.errors)
        self.assertIn("admin_email", form.errors)

    def test_save_model_updates_existing_school_admin(self):
        school = School.objects.create(name="Ecole C", code="EC")
        school_admin = get_user_model().objects.create_user(
            phone="770000004",
            password="testpass123",
            full_name="Ancien Admin",
            email="oldadmin@example.com",
            school=school,
            is_staff=True,
        )
        form = SchoolAdminForm(
            data={
                "name": "Ecole C",
                "code": "EC",
                "address": "",
                "phone": "",
                "email": "ecolec@example.com",
                "is_active": True,
                "admin_full_name": "Nouvel Admin",
                "admin_phone": "770000005",
                "admin_email": "newadmin@example.com",
            },
            instance=school,
        )
        self.assertTrue(form.is_valid(), form.errors)
        request = self._build_request(f"/admin/core/school/{school.pk}/change/")

        self.model_admin.save_model(request, school, form, change=True)

        school_admin.refresh_from_db()
        self.assertEqual(school_admin.full_name, "Nouvel Admin")
        self.assertEqual(school_admin.phone, "770000005")
        self.assertEqual(school_admin.email, "newadmin@example.com")


class SchoolApiAdminProvisionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.superuser = get_user_model().objects.create_superuser(
            phone="770000010",
            password="testpass123",
            full_name="Global Admin API",
            email="global-api@example.com",
        )
        self.client.force_authenticate(self.superuser)

    @patch("core.school_admins.send_school_admin_welcome_email")
    def test_create_school_via_api_creates_school_admin_and_sends_email(self, send_email_mock):
        response = self.client.post(
            "/fr/api/core/schools/",
            {
                "name": "Ecole API",
                "address": "Dakar",
                "phone": "330000000",
                "email": "ecole-api@example.com",
                "is_active": True,
                "admin_full_name": "Admin API",
                "admin_phone": "770000011",
                "admin_email": "admin-api@example.com",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)
        school = School.objects.get(name="Ecole API")
        school_admin = get_user_model().objects.get(phone="770000011")
        self.assertEqual(school_admin.school, school)
        self.assertTrue(school_admin.is_staff)
        send_email_mock.assert_called_once()
