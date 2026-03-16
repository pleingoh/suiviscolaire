from rest_framework import serializers
from .models import Student, Enrollment, StudentParent


class StudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = "__all__"


class EnrollmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Enrollment
        fields = "__all__"


class StudentParentSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentParent
        fields = "__all__"
