from django import forms
from django.contrib import admin
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils.html import format_html

from accounts.notifications import has_real_email_delivery, send_school_admin_welcome_email

from .admin_mixins import SchoolScopedAdminMixin
from .models import ClassRoom, GradeLevel, School, SchoolSetting, SchoolYear, Term
from .school_admins import provision_school_admin

User = get_user_model()


class SchoolAdminForm(forms.ModelForm):
    admin_full_name = forms.CharField(label="Nom complet de l'admin", required=False)
    admin_phone = forms.CharField(label="Telephone de l'admin", required=False)
    admin_email = forms.EmailField(label="Email de l'admin", required=False)

    class Meta:
        model = School
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        school_admin = self.instance.users.filter(is_staff=True, is_superuser=False).order_by("id").first() if self.instance.pk else None
        if school_admin:
            self.fields["admin_full_name"].initial = school_admin.full_name
            self.fields["admin_phone"].initial = school_admin.phone
            self.fields["admin_email"].initial = school_admin.email

    def clean(self):
        cleaned_data = super().clean()
        has_admin_data = any(cleaned_data.get(field) for field in ["admin_full_name", "admin_phone", "admin_email"])
        if not self.instance.pk or has_admin_data:
            required_fields = ["admin_full_name", "admin_phone", "admin_email"]
            missing_fields = [field for field in required_fields if not cleaned_data.get(field)]
            if missing_fields:
                raise forms.ValidationError("Renseigne aussi les informations de connexion de l'admin de l'ecole.")

        if has_admin_data or not self.instance.pk:
            current_admin = self.instance.users.filter(is_staff=True, is_superuser=False).order_by("id").first() if self.instance.pk else None
            current_admin_id = current_admin.pk if current_admin else None

            admin_phone = cleaned_data.get("admin_phone")
            if admin_phone:
                phone_exists = User.objects.filter(phone=admin_phone).exclude(pk=current_admin_id).exists()
                if phone_exists:
                    self.add_error("admin_phone", "Ce telephone est deja utilise par un autre utilisateur.")

            admin_email = cleaned_data.get("admin_email")
            if admin_email:
                email_exists = User.objects.filter(email__iexact=admin_email).exclude(pk=current_admin_id).exists()
                if email_exists:
                    self.add_error("admin_email", "Cet email est deja utilise par un autre utilisateur.")

        return cleaned_data


@admin.register(School)
class SchoolAdmin(SchoolScopedAdminMixin):
    form = SchoolAdminForm
    school_lookup = "id"
    list_display = ("id", "logo_preview", "name", "code", "phone", "email", "is_active")
    search_fields = ("name", "code")
    readonly_fields = ("code",)
    fieldsets = (
        (
            "Informations de l'ecole",
            {
                "fields": ("name", "code", "logo", "address", "phone", "email", "is_active"),
            },
        ),
        (
            "Compte admin de l'ecole",
            {
                "fields": ("admin_full_name", "admin_phone", "admin_email"),
                "description": "Ces champs servent a creer le compte admin propre a cette ecole. Le mot de passe est genere automatiquement et envoye par email.",
            },
        ),
    )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        admin_email = form.cleaned_data.get("admin_email")
        admin_phone = form.cleaned_data.get("admin_phone")
        admin_full_name = form.cleaned_data.get("admin_full_name")

        if admin_email and admin_phone and admin_full_name:
            if not change:
                result = provision_school_admin(
                    school=obj,
                    admin_full_name=admin_full_name,
                    admin_phone=admin_phone,
                    admin_email=admin_email,
                    send_welcome_email=False,
                )

                def send_welcome_email_after_commit():
                    try:
                        send_school_admin_welcome_email(
                            school_name=obj.name,
                            recipient_email=admin_email,
                            full_name=admin_full_name,
                            password=result.generated_password,
                        )
                    except Exception:
                        self.message_user(
                            request,
                            (
                                f"Le compte admin de {obj.name} a ete cree, mais l'email n'a pas pu etre envoye. "
                                f"Mot de passe provisoire: {result.generated_password}"
                            ),
                            level=messages.WARNING,
                        )
                        return

                    if has_real_email_delivery():
                        self.message_user(
                            request,
                            f"Le compte admin de {obj.name} a ete cree et un email a ete envoye a {admin_email}.",
                            level=messages.SUCCESS,
                        )
                    else:
                        self.message_user(
                            request,
                            (
                                f"Le compte admin de {obj.name} a ete cree. "
                                f"L'environnement email est local, donc aucun mail externe n'a ete envoye. "
                                f"Mot de passe provisoire: {result.generated_password}"
                            ),
                            level=messages.WARNING,
                        )

                transaction.on_commit(send_welcome_email_after_commit)
                if has_real_email_delivery():
                    self.message_user(
                        request,
                        f"Le compte admin de {obj.name} a ete cree. Envoi de l'email de bienvenue en cours.",
                        level=messages.SUCCESS,
                    )
                else:
                    self.message_user(
                        request,
                        (
                            f"Le compte admin de {obj.name} a ete cree. "
                            f"L'environnement email est local, donc aucun mail externe n'a ete envoye. "
                            f"Mot de passe provisoire: {result.generated_password}"
                        ),
                        level=messages.WARNING,
                    )
            else:
                provision_school_admin(
                    school=obj,
                    admin_full_name=admin_full_name,
                    admin_phone=admin_phone,
                    admin_email=admin_email,
                )
                self.message_user(
                    request,
                    f"Le compte admin de {obj.name} a ete mis a jour.",
                    level=messages.SUCCESS,
                )

    def logo_preview(self, obj):
        if obj.logo:
            return format_html('<img src="{}" alt="Logo" style="height:40px;width:auto;border-radius:6px;">', obj.logo.url)
        return "-"

    logo_preview.short_description = "Logo"


@admin.register(SchoolYear)
class SchoolYearAdmin(SchoolScopedAdminMixin):
    school_lookup = "school"
    list_display = ("id", "school", "name", "start_date", "end_date", "is_current")
    list_filter = ("school", "is_current")


@admin.register(Term)
class TermAdmin(SchoolScopedAdminMixin):
    school_lookup = "school_year__school"
    list_display = ("id", "school_year", "name", "start_date", "end_date")
    list_filter = ("school_year",)


@admin.register(GradeLevel)
class GradeLevelAdmin(SchoolScopedAdminMixin):
    school_lookup = "school"
    list_display = ("id", "school", "name", "sort_order")
    list_filter = ("school",)


@admin.register(ClassRoom)
class ClassRoomAdmin(SchoolScopedAdminMixin):
    school_lookup = "school_year__school"
    list_display = ("id", "name", "school_year", "grade_level", "capacity")
    list_filter = ("school_year", "grade_level")


@admin.register(SchoolSetting)
class SchoolSettingAdmin(SchoolScopedAdminMixin):
    school_lookup = "school"
    list_display = ("id", "school", "late_after_time", "notify_parents")
