from aiogram import Dispatcher
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from datetime import datetime
from reports.models import Sale, Expense
from aiogram.fsm.state import StatesGroup, State
from asgiref.sync import sync_to_async

class SearchStates(StatesGroup):
    waiting_for_date = State()  # Ожидание даты или диапазона дат

# Функции для получения данных через Django ORM с использованием sync_to_async
@sync_to_async
def get_sales_by_date_range(start_date, end_date):
    sales = Sale.objects.filter(sale_date__gte=start_date, sale_date__lte=end_date)
    return [{"date": sale.sale_date, "amount": sale.total_price, "item": sale.name} for sale in sales]

@sync_to_async
def get_expenses_by_date_range(start_date, end_date):
    expenses = Expense.objects.filter(date__gte=start_date, date__lte=end_date)
    return [{"date": expense.date, "amount": expense.amount, "category": expense.reason} for expense in expenses]

# Хендлер для команды /search
async def search_prompt(message: Message, state: FSMContext):
    await message.answer("Введите дату или диапазон дат в формате:\n"
                         "`YYYY-MM-DD` для одного дня\n"
                         "`YYYY-MM-DD - YYYY-MM-DD` для диапазона", parse_mode="Markdown")
    
    # Переходим в состояние ожидания даты
    await state.set_state(SearchStates.waiting_for_date)

# Хендлер для обработки ввода дат
async def process_search_query(message: Message, state: FSMContext):
    query = message.text.strip()

    try:
        # Если введен диапазон дат
        if " - " in query:
            start_date, end_date = query.split(" - ")
            start_date = datetime.strptime(start_date.strip(), "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date.strip(), "%Y-%m-%d").date()
        else:
            start_date = end_date = datetime.strptime(query, "%Y-%m-%d").date()

        # Получаем данные по продажам и расходам
        sales = await get_sales_by_date_range(start_date, end_date)
        expenses = await get_expenses_by_date_range(start_date, end_date)

        # Формируем ответ
        if not sales and not expenses:
            await message.answer("За указанный период данных нет.")
            return

        response = f"📅 Отчет за период {start_date} - {end_date}\n\n"

        if sales:
            response += "💰 *Продажи:*\n"
            for sale in sales:
                response += f"- {sale['date']} | {sale['amount']} руб. | {sale['item']}\n"

        if expenses:
            response += "\n💸 *Расходы:*\n"
            for expense in expenses:
                response += f"- {expense['date']} | {expense['amount']} руб. | {expense['category']}\n"

        await message.answer(response, parse_mode="Markdown")

    except ValueError:
        await message.answer("Ошибка: Неверный формат даты. Используйте `YYYY-MM-DD` или `YYYY-MM-DD - YYYY-MM-DD`.")

    # Завершаем состояние, т.к. запрос обработан
    await state.clear()
