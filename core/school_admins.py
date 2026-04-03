from dataclasses import dataclass

from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string

from accounts.notifications import send_school_admin_welcome_email

User = get_user_model()


@dataclass
class SchoolAdminProvisionResult:
    school_admin: User
    created: bool
    generated_password: str | None = None


def provision_school_admin(
    *,
    school,
    admin_full_name,
    admin_phone,
    admin_email,
    send_welcome_email=True,
):
    school_admin = school.users.filter(is_staff=True, is_superuser=False).order_by("id").first()
    is_new_admin = school_admin is None
    generated_password = get_random_string(10) if is_new_admin else None

    if is_new_admin:
        school_admin = User.objects.create_user(
            phone=admin_phone,
            password=generated_password,
            full_name=admin_full_name,
            email=admin_email,
            school=school,
            is_staff=True,
        )
    else:
        school_admin.full_name = admin_full_name
        school_admin.phone = admin_phone
        school_admin.email = admin_email
        school_admin.school = school
        school_admin.is_staff = True
        school_admin.is_superuser = False
        school_admin.save(
            update_fields=["full_name", "phone", "email", "school", "is_staff", "is_superuser"]
        )

    school_admin.role = None
    school_admin.save(update_fields=["role"])

    if is_new_admin and send_welcome_email:
        send_school_admin_welcome_email(
            school_name=school.name,
            recipient_email=admin_email,
            full_name=admin_full_name,
            password=generated_password,
        )

    return SchoolAdminProvisionResult(
        school_admin=school_admin,
        created=is_new_admin,
        generated_password=generated_password,
    )
