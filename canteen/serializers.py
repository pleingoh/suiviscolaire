from rest_framework import serializers
from .models import CanteenPlan, CanteenSubscription, CanteenAttendance

class CanteenPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = CanteenPlan
        fields = "__all__"


class CanteenSubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CanteenSubscription
        fields = "__all__"


class CanteenAttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CanteenAttendance
        fields = "__all__"
