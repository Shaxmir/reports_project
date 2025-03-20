# handlers/report_handlers.py
import os
import aiohttp
from datetime import date, datetime
from io import BytesIO
from aiogram import types
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile
from asgiref.sync import sync_to_async
from openpyxl import Workbook
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reports.models import Sale, Expense, CashRegister
from reportlab.lib.utils import simpleSplit
from django.utils.timezone import now

# Регистрация шрифта для кириллицы
pdfmetrics.registerFont(TTFont('DejaVuSans', 'DejaVuSans.ttf'))
pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', 'DejaVuSans-Bold.ttf'))
@sync_to_async
def get_sales_by_date(date):
    return list(Sale.objects.filter(sale_date=date))

@sync_to_async
def get_expenses_by_date(date):
    return list(Expense.objects.filter(date=date))

@sync_to_async
def get_cash_balance_by_date(date):
    return CashRegister.objects.filter(date=date).latest('date').cash_total

def generate_pdf(sales, expenses, cash_balance, report_date):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.setFont("DejaVuSans", 16)
    c.drawString(100, 750, f"Ежедневный отчет на {report_date}")
    c.setFont("DejaVuSans", 12)
    c.drawString(100, 730, "Продажи:")
    y_position = 710
    c.setFont("DejaVuSans", 10)
    payment_method = {'invoice': 'По счету', 'card': 'По карте', 'cash': 'Наличными'}
    for sale in sales:
        sale_text = f"{sale.name} - {sale.quantity} шт - {sale.total_price} руб. - {payment_method[sale.payment_method]} - {sale.sale_date}"
        c.drawString(100, y_position, sale_text)
        y_position -= 15  # Отступ для следующей строки

        if sale.comment:  # Если есть комментарий, добавляем его жирным
            c.setFont("DejaVuSans-Bold", 10)  # Делаем жирный шрифт
            comment_lines = simpleSplit(f"- {sale.comment}", "DejaVuSans-Bold", 10, 400)  # Разбиваем текст, если он длинный
            for line in comment_lines:
                c.drawString(120, y_position, line)  # Чуть правее основного текста
                y_position -= 15  # Отступ вниз
            c.setFont("DejaVuSans", 10)  # Возвращаем обычный шрифт

        y_position -= 10  # Отступ между продажами
    c.setFont("DejaVuSans", 12)
    c.drawString(100, y_position - 20, "Расходы:")
    y_position -= 40
    c.setFont("DejaVuSans", 10)
    for expense in expenses:
        c.drawString(100, y_position, f"{expense.reason} - {expense.amount} руб.")
        y_position -= 15
        if expense.comment:  # Если есть комментарий, добавляем его жирным
            c.setFont("DejaVuSans-Bold", 10)  # Делаем жирный шрифт
            comment_lines = simpleSplit(f"- {expense.comment}", "DejaVuSans-Bold", 10, 400)  # Разбиваем текст, если он длинный
            for line in comment_lines:
                c.drawString(120, y_position, line)  # Чуть правее основного текста
                y_position -= 15  # Отступ вниз
            c.setFont("DejaVuSans", 10)  # Возвращаем обычный шрифт
    c.setFont("DejaVuSans", 12)
    c.drawString(100, y_position - 20, f"Остаток в кассе: {cash_balance} руб.")
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.getvalue()

async def send_report_text(message: Message):
    async with aiohttp.ClientSession() as session:
        async with session.get("http://127.0.0.1:8000/api/report/") as resp:
            data = await resp.json()
            text = f"📊 *Отчет за сегодня:*\n"
            text += f"💰 Продано на {data['total_sales']} руб.\n"
            text += f"   - 💵 Наличными: {data.get('sales_cash', 0)} руб.\n"
            text += f"   - 💳 По карте: {data.get('sales_card', 0)} руб.\n"
            text += f"   - 🏦 По счету: {data.get('sales_invoice', 0)} руб.\n\n"
            text += f"💸 *Расходы: {data['total_expenses']} руб.*\n"
            if data.get("expenses", []):
                for expense in data["expenses"]:
                    text += f"   - {expense['reason']}: {expense['amount']} руб.\n\n"
            else:
                text += "   - ❌ Нет расходов.\n\n"
            text += f"🛠 Остаток в кассе: {data['cash_total']} руб."
            await message.answer(text, parse_mode="Markdown")

async def send_report_pdf(message: Message):
    today = now().date()
    sales = await get_today_sales()
    expenses = await get_today_expenses()
    if not sales and not expenses:
        await message.answer("❌ Нет данных о продажах и расходах за сегодня.")
        return
    cash_balance = await get_cash_balance()
    pdf_data = generate_pdf(sales, expenses, cash_balance)
    pdf_filename = "report.pdf"
    with open(pdf_filename, "wb") as f:
        f.write(pdf_data)
    pdf_file = FSInputFile(pdf_filename, filename=f"Отчет_на_{today}.pdf")
    await message.answer_document(pdf_file, caption="Отчет за сегодняшний день")
    os.remove(pdf_filename)



###################


@sync_to_async
def get_unique_dates():
    # Получаем уникальные даты из таблицы Sale
    sales_dates = Sale.objects.dates('sale_date', 'day').distinct()
    # Получаем уникальные даты из таблицы Expense
    expenses_dates = Expense.objects.dates('date', 'day').distinct()
    # Объединяем и сортируем даты
    all_dates = sorted(set(sales_dates) | set(expenses_dates), reverse=True)
    return all_dates


# Кнопки пагинации

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

async def create_dates_keyboard(page: int = 0, items_per_page: int = 5):
    """
    Создает инлайн-клавиатуру с датами и пагинацией.
    """
    dates = await get_unique_dates()
    total_dates = len(dates)
    total_pages = (total_dates + items_per_page - 1) // items_per_page

    # Ограничиваем страницы
    if page < 0:
        page = 0
    elif page >= total_pages:
        page = total_pages - 1

    # Получаем даты для текущей страницы
    start = page * items_per_page
    end = start + items_per_page
    current_dates = dates[start:end]

    # Создаем клавиатуру
    builder = InlineKeyboardBuilder()
    for date in current_dates:
        builder.button(text=date.strftime("%Y-%m-%d"), callback_data=f"report_date:{date}")

    # Добавляем кнопки пагинации
    if page > 0:
        builder.button(text="⬅️ Назад", callback_data=f"report_page:{page - 1}")
    if page < total_pages - 1:
        builder.button(text="Вперед ➡️", callback_data=f"report_page:{page + 1}")

    builder.adjust(1)  # Одна кнопка на строку
    return builder.as_markup()


async def handle_report_by_date(message: Message):
    keyboard = await create_dates_keyboard()
    await message.answer("Выберите дату для отчета:", reply_markup=keyboard)



from aiogram import F

async def handle_report_date_selection(callback: types.CallbackQuery):
    """
    Обработчик выбора даты для отчета.
    """
    # Извлекаем дату из callback_data
    date_str = callback.data.split(":")[1]
    report_date = datetime.strptime(date_str, "%Y-%m-%d").date()

    # Получаем данные за выбранную дату
    sales = await get_sales_by_date(report_date)
    expenses = await get_expenses_by_date(report_date)
    if not sales and not expenses:
        await callback.answer("❌ Нет данных за выбранную дату.", show_alert=True)
        return

    # Формируем PDF-отчет
    cash_balance = await get_cash_balance_by_date(report_date)
    pdf_data = generate_pdf(sales, expenses, cash_balance, report_date)
    pdf_filename = f"report_{report_date}.pdf"
    with open(pdf_filename, "wb") as f:
        f.write(pdf_data)

    # Отправляем PDF-файл
    pdf_file = FSInputFile(pdf_filename, filename=f"Отчет_на_{report_date}.pdf")
    await callback.message.answer_document(pdf_file, caption=f"Отчет за {report_date}")
    os.remove(pdf_filename)

    # Закрываем уведомление о нажатии кнопки
    await callback.answer()


async def handle_report_pagination(callback: types.CallbackQuery):
    """
    Обработчик пагинации для клавиатуры с датами.
    """
    # Извлекаем номер страницы из callback_data
    page = int(callback.data.split(":")[1])

    # Обновляем клавиатуру с новой страницей
    keyboard = await create_dates_keyboard(page)
    await callback.message.edit_reply_markup(reply_markup=keyboard)

    # Закрываем уведомление о нажатии кнопки
    await callback.answer()