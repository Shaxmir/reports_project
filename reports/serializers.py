from rest_framework import serializers
from .models import Sale, Expense, CashRegister

class SaleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sale
        fields = '__all__'

class ExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = '__all__'

    def create(self, validated_data):
        expense = super().create(validated_data)
        today = expense.date
        cash, created = CashRegister.objects.get_or_create(date=today)
        cash.cash_total -= expense.amount
        cash.cash_total = max(0, cash.cash_total)  # Защита от отрицательных значений
        cash.save()
        return expense


class CashRegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = CashRegister
        fields = '__all__'
