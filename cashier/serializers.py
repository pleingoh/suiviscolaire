from rest_framework import serializers
from .models import CashTransaction

class CashTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CashTransaction
        fields = "__all__"
        read_only_fields = ("created_by", "validated_by", "created_at", "validated_at")

    def validate(self, attrs):
        service = attrs.get("service") or getattr(self.instance, "service", None)
        tx_type = attrs.get("transaction_type") or getattr(self.instance, "transaction_type", None)

        student = attrs.get("student") or getattr(self.instance, "student", None)
        canteen_month = attrs.get("canteen_month") or getattr(self.instance, "canteen_month", None)

        if service == "CANTINE" and tx_type == "IN":
            if not student:
                raise serializers.ValidationError({"student": "Obligatoire pour une transaction cantine"})
            if not canteen_month:
                raise serializers.ValidationError({"canteen_month": "Obligatoire pour une transaction cantine"})
        return attrs
