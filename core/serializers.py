from rest_framework import serializers
from .models import School, SchoolYear, Term, GradeLevel, ClassRoom

class SchoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = School
        fields = "__all__"

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
