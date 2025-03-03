from django.db import models
from decimal import Decimal

class Sale(models.Model):
    PAYMENT_METHODS = [
        ('invoice', 'По счету'),
        ('card', 'Картой'),
        ('cash', 'Наличными'),
    ]

    name = models.CharField(max_length=255, verbose_name="Название фанеры")
    quantity = models.PositiveIntegerField(verbose_name="Количество проданное")
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена за единицу")
    total_price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Общая сумма", blank=True)
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHODS, verbose_name="Способ оплаты")
    sale_date = models.DateField(verbose_name="Дата продажи")
    shipment_date = models.DateField(verbose_name="Дата отгрузки")
    comment = models.TextField(blank=True, verbose_name="Комментарий")

    def save(self, *args, **kwargs):
        self.total_price = self.quantity * self.price_per_unit
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} - {self.quantity} шт."

class Expense(models.Model):
    reason = models.CharField(max_length=255, verbose_name="Причина расхода")
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Сумма")
    comment = models.TextField(blank=True, verbose_name="Комментарий")
    date = models.DateField(verbose_name="Дата")

    def __str__(self):
        return f"{self.reason} - {self.amount} руб."

class CashRegister(models.Model):
    date = models.DateField(auto_now_add=True, verbose_name="Дата")
    cash_total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), verbose_name="Остаток в кассе")  # Используем DecimalField

    def __str__(self):
        return f"Касса на {self.date}: {self.cash_total} руб."
