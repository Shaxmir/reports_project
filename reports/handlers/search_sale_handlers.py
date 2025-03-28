from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State
from aiogram.fsm.filters import Command
from aiogram.types import BufferedInputFile
from datetime import datetime
from reports.models import Sale

from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from datetime import datetime



def generate_pdf_report(sales, start_date=None, end_date=None):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.setFont("Helvetica", 16)
    title = "Отчет о продажах"
    if start_date and end_date:
        title += f" с {start_date.strftime('%Y-%m-%d')} по {end_date.strftime('%Y-%m-%d')}"
    c.drawString(100, 750, title)
    c.setFont("Helvetica", 12)
    y_position = 730
    total_quantity = 0
    total_amount = 0
    payment_totals = {"cash": 0, "card": 0, "invoice": 0}

    for sale in sales:
        sale_text = f"{sale.name} - {sale.quantity} шт - {sale.total_price} руб. - {sale.payment_method} - {sale.sale_date}"
        c.drawString(100, y_position, sale_text)
        y_position -= 15
        total_quantity += sale.quantity
        total_amount += sale.total_price
        payment_totals[sale.payment_method] += sale.total_price

    c.setFont("Helvetica-Bold", 12)
    c.drawString(100, y_position - 20, f"Всего продано: {total_quantity} шт, на сумму {total_amount} руб.")
    c.drawString(100, y_position - 40, f"Наличными: {payment_totals['cash']} руб., Картой: {payment_totals['card']} руб., По счету: {payment_totals['invoice']} руб.")
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.getvalue()



class SearchSaleState(State):
    keywords = State()  # Для ввода ключевых слов
    period_choice = State()  # Выбор периода
    date_range = State()  # Даты для периода

# Хендлер для команды /search_sale
async def search_sale_handler(message: types.Message):
    await message.answer("Введите ключевые слова для поиска товаров:")
    await SearchSaleState.keywords.set()  # Сохраняем состояние

# Хендлер для обработки ключевых слов
async def process_search_keywords(message: types.Message, state: FSMContext):
    query = message.text.strip()
    await state.update_data(query=query)  # Сохраняем введенные ключевые слова

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="За все время", callback_data="search_all")],
            [InlineKeyboardButton(text="За определенный период", callback_data="search_period")]
        ]
    )
    await message.answer("Выберите период:", reply_markup=keyboard)
    await SearchSaleState.period_choice.set()  # Переходим к выбору периода

# Хендлер для выбора периода
async def process_search_period(callback: types.CallbackQuery, state: FSMContext):
    action = callback.data
    user_data = await state.get_data()
    query = user_data.get('query')

    if action == "search_all":
        sales = Sale.objects.filter(name__icontains=query)
        if not sales.exists():
            await callback.message.answer("Продажи с такими параметрами не найдены.")
            return
        pdf_data = generate_pdf_report(sales)
        await callback.message.answer_document(BufferedInputFile(pdf_data, filename="sales_report.pdf"))
    elif action == "search_period":
        await callback.message.answer("Введите период в формате YYYY-MM-DD - YYYY-MM-DD")
        await SearchSaleState.date_range.set()  # Переход к вводу дат

# Хендлер для обработки ввода даты
async def process_search_date_range(message: types.Message, state: FSMContext):
    try:
        period = message.text.strip()
        start_date, end_date = map(str.strip, period.split("-"))
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
        end_date = datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        await message.answer("Некорректный формат. Введите даты в формате YYYY-MM-DD - YYYY-MM-DD")
        return

    user_data = await state.get_data()
    query = user_data.get('query')

    sales = Sale.objects.filter(
        name__icontains=query,
        sale_date__range=(start_date, end_date)
    )

    if not sales.exists():
        await message.answer("Продажи с такими параметрами за указанный период не найдены.")
        return

    pdf_data = generate_pdf_report(sales, start_date, end_date)
    await message.answer_document(BufferedInputFile(pdf_data, filename="sales_report.pdf"))
    await state.finish()  # Завершаем состояние
