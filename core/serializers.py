from rest_framework import serializers

from .models import School, SchoolYear, Term, GradeLevel, ClassRoom
from .school_admins import provision_school_admin

class SchoolSerializer(serializers.ModelSerializer):
    admin_full_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    admin_phone = serializers.CharField(write_only=True, required=False, allow_blank=True)
    admin_email = serializers.EmailField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = School
        fields = (
            "id",
            "name",
            "code",
            "logo",
            "address",
            "phone",
            "email",
            "is_active",
            "admin_full_name",
            "admin_phone",
            "admin_email",
        )
        read_only_fields = ("id", "code")

    def validate(self, attrs):
        attrs = super().validate(attrs)
        admin_values = {
            "admin_full_name": attrs.get("admin_full_name", ""),
            "admin_phone": attrs.get("admin_phone", ""),
            "admin_email": attrs.get("admin_email", ""),
        }
        has_admin_data = any(admin_values.values())
        if has_admin_data and not all(admin_values.values()):
            raise serializers.ValidationError(
                "Renseigne aussi les informations de connexion de l'admin de l'ecole."
            )
        return attrs

    def create(self, validated_data):
        admin_full_name = validated_data.pop("admin_full_name", "")
        admin_phone = validated_data.pop("admin_phone", "")
        admin_email = validated_data.pop("admin_email", "")

        school = super().create(validated_data)
        if admin_full_name and admin_phone and admin_email:
            provision_school_admin(
                school=school,
                admin_full_name=admin_full_name,
                admin_phone=admin_phone,
                admin_email=admin_email,
            )
        return school

    def update(self, instance, validated_data):
        admin_full_name = validated_data.pop("admin_full_name", "")
        admin_phone = validated_data.pop("admin_phone", "")
        admin_email = validated_data.pop("admin_email", "")

        school = super().update(instance, validated_data)
        if admin_full_name and admin_phone and admin_email:
            provision_school_admin(
                school=school,
                admin_full_name=admin_full_name,
                admin_phone=admin_phone,
                admin_email=admin_email,
            )
        return school

class SchoolYearSerializer(serializers.ModelSerializer):
    class Meta:
        model = SchoolYear
        fields = "__all__"

class TermSerializer(serializers.ModelSerializer):
    class Meta:
        model = Term
        fields = "__all__"

class GradeLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = GradeLevel
        fields = "__all__"

class ClassRoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClassRoom
        fields = "__all__"
