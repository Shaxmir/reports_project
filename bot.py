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
from aiogram import F

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Импорт обработчиков из пакета handlers
from reports.handlers import sale_handlers, expense_handlers, cash_handlers, report_handlers, expenses_edit_handlers, sale_edit_handlers, reports_monthly_handlers, search_handler, search_sale_handlers
from reports.handlers.expenses_edit_handlers import EditExpenseState
from reports.handlers.search_handler import SearchStates
from reports.filters.role_filters import IsAdmin, IsCreator

# Регистрируем хендлеры для продажи
dp.message.register(sale_handlers.start_sale, Command("sale"), IsAdmin())
dp.message.register(sale_handlers.process_name, sale_handlers.SaleState.name)
dp.message.register(sale_handlers.process_quantity, sale_handlers.SaleState.quantity)
dp.message.register(sale_handlers.process_price, sale_handlers.SaleState.price)
dp.message.register(sale_handlers.process_payment, sale_handlers.SaleState.payment_method)
dp.message.register(sale_handlers.process_sale_date, sale_handlers.SaleState.sale_date)
dp.message.register(sale_handlers.process_shipment_date, sale_handlers.SaleState.shipment_date)
dp.message.register(sale_handlers.process_comment, sale_handlers.SaleState.comment)

# Регистрация обработчиков для callback-запросов
dp.message.register(sale_edit_handlers.get_all_sales, Command("sales"), IsAdmin())
dp.callback_query.register(sale_edit_handlers.show_sale_info, lambda c: c.data.startswith("sale_"), IsAdmin())
dp.callback_query.register(sale_edit_handlers.delete_sale, lambda c: c.data.startswith("delete_sale_"), IsAdmin())
dp.callback_query.register(sale_edit_handlers.start_edit_sale, lambda c: c.data.startswith("edit_sale_"), IsAdmin())

# Регистрация обработчиков для изменения продажи
dp.message.register(sale_edit_handlers.process_edit_name, sale_edit_handlers.EditSaleState.name)
dp.message.register(sale_edit_handlers.process_edit_quantity, sale_edit_handlers.EditSaleState.quantity)
dp.message.register(sale_edit_handlers.process_edit_price, sale_edit_handlers.EditSaleState.price)
dp.message.register(sale_edit_handlers.process_edit_payment, sale_edit_handlers.EditSaleState.payment_method)
dp.message.register(sale_edit_handlers.process_edit_comment, sale_edit_handlers.EditSaleState.comment)

# Регистрируем хендлеры для расходов
dp.message.register(expense_handlers.start_expense, Command("expense"), IsAdmin())
dp.message.register(expense_handlers.process_reason, expense_handlers.ExpenseState.reason)
dp.message.register(expense_handlers.process_amount, expense_handlers.ExpenseState.amount)
dp.message.register(expense_handlers.process_expense_comment, expense_handlers.ExpenseState.comment)

# Редактирование и удаление расходов
dp.message.register(expenses_edit_handlers.get_expenses, Command("expenses"), IsAdmin())  # Вывод списка расходов
dp.callback_query.register(expenses_edit_handlers.delete_expense_callback, lambda c: c.data.startswith("delete_expense_"), IsAdmin())  # Удаление
dp.callback_query.register(expenses_edit_handlers.edit_expense_callback, lambda c: c.data.startswith("edit_expense_"), IsAdmin())  # Изменение
dp.message.register(expenses_edit_handlers.edit_expense_amount, EditExpenseState.amount)  # Ввод суммы
dp.message.register(expenses_edit_handlers.edit_expense_comment, EditExpenseState.comment)  # Ввод комментария
dp.message.register(expenses_edit_handlers.edit_expense_reason, EditExpenseState.reason)  # Ввод причины

# Регистрируем хендлеры для работы с кассой
dp.message.register(cash_handlers.start_cash, Command("cash"), IsAdmin())
dp.message.register(cash_handlers.process_cash, cash_handlers.CashState.amount)

# Регистрируем хендлеры для отчетов
dp.message.register(report_handlers.send_report_text, Command("report"))
dp.message.register(report_handlers.send_report_pdf, Command("report_pdf"))
dp.message.register(sale_handlers.get_all_sales, Command("all_sales"))

# Отчеты старые
dp.message.register(report_handlers.handle_report_by_date, Command("report_by_date"))

# Регистрируем callback-хендлеры для отчетов
dp.callback_query.register(report_handlers.handle_report_date_selection, F.data.startswith("report_date:"))
dp.callback_query.register(report_handlers.handle_report_pagination, F.data.startswith("report_page:"))

# Отчеты за месяц
dp.message.register(reports_monthly_handlers.monthly_report_start, Command("monthly_report"))
dp.callback_query.register(reports_monthly_handlers.handle_year_selection, F.data.startswith("year_"))
dp.callback_query.register(reports_monthly_handlers.handle_month_selection, F.data.startswith("month_"))


# Регистрируем хендлеры для поиска
dp.message.register(search_handler.search_prompt, Command("search"))
dp.message.register(search_handler.process_search_query, search_handler.SearchStates.waiting_for_date)

# Регистрация хендлеров поиска по товарам
dp.message.register(search_sale_handlers.search_sale_start, Command("search_sale"))
dp.message.register(search_sale_handlers.process_search_query, search_sale_handlers.SearchSale.waiting_for_query)
dp.message.register(search_sale_handlers.process_period_input, search_sale_handlers.SearchSale.waiting_for_period)
dp.message.register(search_sale_handlers.process_query_with_period, search_sale_handlers.SearchSale.waiting_for_query_with_period)
dp.callback_query.register(search_sale_handlers.handle_period_choice, F.data.in_(["all_time", "specific_period"]))

# Простой стартовый хендлер
@dp.message(Command("start"))
async def start_cmd(message: Message):
    user_id = message.from_user.id
    print(f"User ID: {user_id}")
    await message.answer(f"Привет! Отправь команду или выбери ее в меню комнад.\n/sale, чтобы добавить продажу\n/expense для расхода\n/cash для пополнения кассы\n/report для отчета\n/all_sales для просмотра сегодняшних продаж\n/report_pdf получить отчет в формате PDF")

@dp.message(Command("myid"))
async def start_cmd(message: Message):
    user_id = message.from_user.id
    await message.answer(f"Привет! Твой ID {user_id}.\nОтправь его @shaxsodo если хочешь получить права пользования")

async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
