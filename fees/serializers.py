from rest_framework import serializers
from .models import FeePlan, StudentFeeAccount, FeeInstallment


class FeePlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeePlan
        fields = "__all__"


class StudentFeeAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentFeeAccount
        fields = "__all__"


class FeeInstallmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeeInstallment
        fields = "__all__"
