from aiogram.types import Message
from aiogram.filters import Command
from datetime import datetime
from reports.models import Sale, Expense
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

async def get_sales_by_date_range(start_date, end_date):
    async with AsyncSession() as session:
        result = await session.execute(
            select(Sale).where(Sale.date >= start_date, Sale.date <= end_date)
        )
        sales = result.scalars().all()
        return [{"date": s.date, "amount": s.amount, "item": s.item} for s in sales]

async def get_expenses_by_date_range(start_date, end_date):
    async with AsyncSession() as session:
        result = await session.execute(
            select(Expense).where(Expense.date >= start_date, Expense.date <= end_date)
        )
        expenses = result.scalars().all()
        return [{"date": e.date, "amount": e.amount, "category": e.category} for e in expenses]

async def search_prompt(message: Message):
    await message.answer("Введите дату или диапазон дат в формате:\n"
                         "`YYYY-MM-DD` для одного дня\n"
                         "`YYYY-MM-DD - YYYY-MM-DD` для диапазона", parse_mode="Markdown")

async def process_search_query(message: Message):
    query = message.text.strip()

    try:
        if " - " in query:
            start_date, end_date = query.split(" - ")
            start_date = datetime.strptime(start_date.strip(), "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date.strip(), "%Y-%m-%d").date()
        else:
            start_date = end_date = datetime.strptime(query, "%Y-%m-%d").date()

        sales = await get_sales_by_date_range(start_date, end_date)
        expenses = await get_expenses_by_date_range(start_date, end_date)

        if not sales and not expenses:
            await message.answer("За указанный период данных нет.")
            return

        response = f"📅 Отчет за период {start_date} - {end_date}\n\n"

        if sales:
            response += "💰 *Продажи:*\n"
            for sale in sales:
                response += f"- {sale['date']}: {sale['amount']} руб. ({sale['item']})\n"

        if expenses:
            response += "\n💸 *Расходы:*\n"
            for expense in expenses:
                response += f"- {expense['date']}: {expense['amount']} руб. ({expense['category']})\n"

        await message.answer(response, parse_mode="Markdown")

    except ValueError:
        await message.answer("Ошибка: Неверный формат даты. Используйте `YYYY-MM-DD` или `YYYY-MM-DD - YYYY-MM-DD`.")
