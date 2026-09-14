"""Response shapes for the generated schema. Views build the payloads."""

from __future__ import annotations

from rest_framework import serializers

from apps.common.serializers import MoneySerializer


class PeriodSerializer(serializers.Serializer):
    start = serializers.DateField()
    end = serializers.DateField()
    days = serializers.IntegerField()

    class Meta:
        ref_name = "ReportPeriod"


class BucketSerializer(serializers.Serializer):
    orders = serializers.IntegerField()
    gross = MoneySerializer()

    class Meta:
        ref_name = "SalesBucket"


class DailySalesSerializer(BucketSerializer):
    date = serializers.DateField()

    class Meta:
        ref_name = "DailySales"


class SalesReportSerializer(serializers.Serializer):
    period = PeriodSerializer()
    orders = serializers.IntegerField()
    gross = MoneySerializer()
    refunds = MoneySerializer()
    net = MoneySerializer()
    average_order = MoneySerializer()
    subtotal = MoneySerializer()
    discounts = MoneySerializer()
    delivery_fees = MoneySerializer()
    service_charges = MoneySerializer()
    vat = MoneySerializer()
    tips = MoneySerializer()
    average_prep_minutes = serializers.FloatField(allow_null=True)
    by_payment_method = serializers.DictField(child=BucketSerializer())
    by_fulfilment = serializers.DictField(child=BucketSerializer())
    incomplete_orders = serializers.DictField(child=serializers.IntegerField())
    daily = DailySalesSerializer(many=True)

    class Meta:
        ref_name = "SalesReport"


class PopularItemSerializer(serializers.Serializer):
    slug = serializers.CharField(allow_blank=True)
    name = serializers.CharField()
    quantity = serializers.IntegerField()
    orders = serializers.IntegerField()
    revenue = MoneySerializer()

    class Meta:
        ref_name = "PopularItem"


class PopularItemsReportSerializer(serializers.Serializer):
    period = PeriodSerializer()
    items = PopularItemSerializer(many=True)

    class Meta:
        ref_name = "PopularItemsReport"


class BusiestSlotSerializer(serializers.Serializer):
    weekday = serializers.CharField()
    hour = serializers.IntegerField()
    orders = serializers.IntegerField()

    class Meta:
        ref_name = "BusiestSlot"


class PeakHoursReportSerializer(serializers.Serializer):
    period = PeriodSerializer()
    weekdays = serializers.ListField(child=serializers.CharField())
    grid = serializers.ListField(child=serializers.ListField(child=serializers.IntegerField()))
    by_hour = serializers.ListField(child=serializers.IntegerField())
    busiest = BusiestSlotSerializer(allow_null=True)

    class Meta:
        ref_name = "PeakHoursReport"


class RiderRowSerializer(serializers.Serializer):
    rider = serializers.CharField()
    deliveries = serializers.IntegerField()
    failed = serializers.IntegerField()
    average_delivery_minutes = serializers.FloatField(allow_null=True)
    on_time_percent = serializers.IntegerField(allow_null=True)
    cash_collected = MoneySerializer()

    class Meta:
        ref_name = "RiderPerformance"


class RiderReportSerializer(serializers.Serializer):
    period = PeriodSerializer()
    riders = RiderRowSerializer(many=True)

    class Meta:
        ref_name = "RiderReport"
