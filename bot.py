# bot.py
import os
import django
import asyncio
import logging

# Настройка Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sales_reports.settings")
django.setup()

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sales_reports.settings import BOT_TOKEN

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Импорт обработчиков из пакета handlers
from reports.handlers import sale_handlers, expense_handlers, cash_handlers, report_handlers

# Регистрируем хендлеры для продажи
dp.message.register(sale_handlers.start_sale, Command("sale"))
dp.message.register(sale_handlers.process_name, sale_handlers.SaleState.name)
dp.message.register(sale_handlers.process_quantity, sale_handlers.SaleState.quantity)
dp.message.register(sale_handlers.process_price, sale_handlers.SaleState.price)
dp.message.register(sale_handlers.process_payment, sale_handlers.SaleState.payment_method)
dp.message.register(sale_handlers.process_sale_date, sale_handlers.SaleState.sale_date)
dp.message.register(sale_handlers.process_shipment_date, sale_handlers.SaleState.shipment_date)
dp.message.register(sale_handlers.process_comment, sale_handlers.SaleState.comment)

# Регистрируем хендлеры для расходов
dp.message.register(expense_handlers.start_expense, Command("expense"))
dp.message.register(expense_handlers.process_reason, expense_handlers.ExpenseState.reason)
dp.message.register(expense_handlers.process_amount, expense_handlers.ExpenseState.amount)
dp.message.register(expense_handlers.process_expense_comment, expense_handlers.ExpenseState.comment)

# Регистрируем хендлеры для работы с кассой
dp.message.register(cash_handlers.start_cash, Command("cash"))
dp.message.register(cash_handlers.process_cash, cash_handlers.CashState.amount)

# Регистрируем хендлеры для отчетов
dp.message.register(report_handlers.send_report_text, Command("report"))
dp.message.register(report_handlers.send_report_pdf, Command("report_pdf"))
dp.message.register(sale_handlers.get_all_sales, Command("all_sales"))

# Простой стартовый хендлер
@dp.message(Command("start"))
async def start_cmd(message: Message):
    await message.answer("Привет! Отправь команду или выбери ее в меню комнад.\n/sale, чтобы добавить продажу\n/expense для расхода\n/cash для пополнения кассы\n/report для отчета\n/all_sales для просмотра сегодняшних продаж\n/report_pdf получить отчет в формате PDF")

async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
