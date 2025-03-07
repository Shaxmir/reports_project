from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets
from .models import Sale, Expense, CashRegister
from .serializers import SaleSerializer, ExpenseSerializer, CashRegisterSerializer
from django.utils.timezone import now
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import logging
from decimal import Decimal

logger = logging.getLogger(__name__)

class SaleViewSet(viewsets.ModelViewSet):
    queryset = Sale.objects.all()
    serializer_class = SaleSerializer

class ExpenseViewSet(viewsets.ModelViewSet):
    queryset = Expense.objects.all()
    serializer_class = ExpenseSerializer

class CashRegisterViewSet(viewsets.ModelViewSet):
    queryset = CashRegister.objects.all()
    serializer_class = CashRegisterSerializer


from django.db.models import Sum
from django.http import JsonResponse
from django.utils.timezone import now
from .models import Sale, Expense, CashRegister

def daily_report(request):
    today = now().date()
    
    sales = Sale.objects.filter(sale_date=today)
    expenses = Expense.objects.filter(date=today)
    cash = CashRegister.objects.filter(date=today).last()

    total_sales = sales.aggregate(Sum("total_price"))["total_price__sum"] or 0
    total_expenses = expenses.aggregate(Sum("amount"))["amount__sum"] or 0

    # Разделение продаж по методам оплаты
    sales_cash = sales.filter(payment_method="cash").aggregate(Sum("total_price"))["total_price__sum"] or 0
    sales_card = sales.filter(payment_method="card").aggregate(Sum("total_price"))["total_price__sum"] or 0
    sales_invoice = sales.filter(payment_method="invoice").aggregate(Sum("total_price"))["total_price__sum"] or 0

    # Если фиксировали кассу, используем ее сумму
    cash_total = cash.cash_total if cash else 0


    # Учитываем продажи за наличные
    # cash_total = sales_cash

    # Вычитаем расходы
    # cash_total -= total_expenses
    cash_total = max(0, cash_total)  # Защита от отрицательных значений

    # Формируем список расходов
    expense_list = list(expenses.values("reason", "amount"))

    data = {
        "total_sales": total_sales,
        "sales_cash": sales_cash,
        "sales_card": sales_card,
        "sales_invoice": sales_invoice,
        "total_expenses": total_expenses,
        "expenses": expense_list,
        "cash_total": cash_total
    }

    return JsonResponse(data)



from django.db import transaction

from django.db import transaction

@csrf_exempt
@transaction.atomic
def add_expense(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            amount = Decimal(data.get("amount", 0))
            reason = data.get("reason", "Не указана")
            comment = data.get("comment", "")
            today = now().date()

            # Получаем или создаем запись кассы на сегодня
            cash, created = CashRegister.objects.get_or_create(date=today)
            logger.debug(f"Получен расход: {amount}, текущая касса: {cash.cash_total}")
            # Вычитаем сумму расхода
            cash.cash_total -= amount
            cash.save()
            logger.debug(f"Касса обновлена: id={cash.id}, cash_total={cash.cash_total}")

            # Создаем запись о расходе
            Expense.objects.create(
                reason=reason,
                amount=amount,
                comment=comment,
                date=today
            )

            return JsonResponse({"message": "✅ Расход добавлен!", "cash_total": str(cash.cash_total)}, status=201)
        except Exception as e:
            logger.error(f"Ошибка при добавлении расхода: {e}")
            return JsonResponse({"error": "Внутренняя ошибка сервера"}, status=500)

    return JsonResponse({"error": "Метод не поддерживается"}, status=405)

# Изменения расхода
@csrf_exempt
@transaction.atomic
def update_expense(request, expense_id):
    if request.method == "PATCH":
        try:
            data = json.loads(request.body)
            new_amount = data.get("amount")
            expense = Expense.objects.get(id=expense_id)

            if new_amount:
                expense.amount = new_amount
                expense.save()
                return JsonResponse({"message": "✅ Расход обновлен!"}, status=200)

            return JsonResponse({"error": "Некорректные данные!"}, status=400)
        except Expense.DoesNotExist:
            return JsonResponse({"error": "Расход не найден!"}, status=404)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Метод не поддерживается"}, status=405)





@csrf_exempt
def update_cash(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            amount = Decimal(data.get("amount", 0))  # Преобразуем к Decimal

            if amount <= 0:
                logger.error("Попытка добавить неположительное значение!")
                return JsonResponse({"error": "Сумма пополнения должна быть положительной!"}, status=400)

            today = now().date()

            # Логируем, что происходит при получении или создании записи
            cash, created = CashRegister.objects.get_or_create(date=today)
            logger.debug(f"Найдена/создана запись для {today}: {cash}, Создано? {created}")

            # Прибавляем деньги к кассе, теперь все типы Decimal
            cash.cash_total += amount
            cash.save(update_fields=["cash_total"])

            logger.debug(f"Новый баланс: {cash.cash_total}")
            return JsonResponse({"message": "✅ Касса обновлена!", "cash_total": str(cash.cash_total)}, status=201)
        except Exception as e:
            logger.error(f"Ошибка при обновлении кассы: {e}")
            return JsonResponse({"error": f"Внутренняя ошибка: {str(e)}"}, status=500)

    return JsonResponse({"error": "Метод не поддерживается"}, status=405)
