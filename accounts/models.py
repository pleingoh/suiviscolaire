from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class Role(models.Model):
    code = models.CharField(max_length=30, unique=True)
    label = models.CharField(max_length=60)

    class Meta:
        verbose_name = "Role"
        verbose_name_plural = "Roles"

    def __str__(self):
        return self.label


class UserManager(BaseUserManager):
    def create_user(self, phone, password=None, **extra_fields):
        if not phone:
            raise ValueError("Le telephone est obligatoire")
        user = self.model(phone=phone, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        return self.create_user(phone, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    full_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=30, unique=True)
    email = models.EmailField(blank=True, null=True)
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"

    def __str__(self):
        return f"{self.full_name} ({self.phone})"
