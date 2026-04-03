from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import AdminPasswordChangeForm, ReadOnlyPasswordHashField

from core.access import is_global_admin

from .models import Role, User


class UserCreationForm(forms.ModelForm):
    password1 = forms.CharField(label="Mot de passe", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirmation", widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ("phone", "full_name", "email", "role", "school", "is_active", "is_staff")

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Les mots de passe ne correspondent pas.")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class UserChangeForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField(label="Mot de passe")

    class Meta:
        model = User
        fields = (
            "phone",
            "full_name",
            "email",
            "password",
            "role",
            "school",
            "is_active",
            "is_staff",
            "is_superuser",
            "groups",
            "user_permissions",
        )

    def clean_password(self):
        return self.initial["password"]


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "label")
    search_fields = ("code", "label")

    def has_module_permission(self, request):
        return is_global_admin(request.user)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm

    list_display = ("phone", "full_name", "role", "school", "is_staff", "is_active")
    list_filter = ("is_staff", "is_active", "is_superuser", "role", "school")
    search_fields = ("phone", "full_name", "email")
    ordering = ("phone",)
    filter_horizontal = ("groups", "user_permissions")

    fieldsets = (
        (None, {"fields": ("phone", "password")}),
        ("Informations personnelles", {"fields": ("full_name", "email", "role", "school")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Dates importantes", {"fields": ("last_login",)}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("phone", "full_name", "email", "role", "school", "password1", "password2", "is_active", "is_staff"),
            },
        ),
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if is_global_admin(request.user):
            return queryset
        if request.user.school_id:
            return queryset.filter(school=request.user.school, is_superuser=False)
        return queryset.none()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "school" and not is_global_admin(request.user):
            kwargs["queryset"] = db_field.remote_field.model.objects.filter(id=request.user.school_id)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if not is_global_admin(request.user):
            obj.school = request.user.school
            obj.is_superuser = False
            obj.is_staff = True
        super().save_model(request, obj, form, change)
