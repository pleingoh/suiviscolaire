from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import School


class UserSchoolPersistenceTests(TestCase):
    def test_user_school_is_saved(self):
        school = School.objects.create(name="Ecole Test", code="TEST")
        user = get_user_model().objects.create_user(
            phone="772222222",
            password="secret123",
            full_name="Admin Ecole",
            school=school,
            is_staff=True,
        )

        self.assertEqual(user.school, school)

# Create your tests here.
