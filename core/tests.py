from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import Role
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
