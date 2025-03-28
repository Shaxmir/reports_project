from aiogram import types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram import types
from aiogram.filters import Command
from aiogram.utils.markdown import hbold
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from django.db.models import Q, Sum
from reports.models import Sale
from datetime import datetime
import asyncio
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

# Создаем группу состояний
class SearchSaleState(StatesGroup):
    keywords = State()
    period_choice = State()
    date_range = State()


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

# Команда для запуска поиска
async def search_sale(message: Message, state: FSMContext):
    await message.answer("Введите ключевые слова для поиска фанеры (например, '12мм F/W'):")
    await state.set_state(SearchSaleState.keywords)

# Обрабатываем ключевые слова
async def process_search_keywords(message: Message, state: FSMContext):
    keywords = message.text.lower().split()  # Преобразуем в нижний регистр и разбиваем на слова
    await state.update_data(keywords=keywords)

    # Создаем клавиатуру с вариантами выбора
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="За все время")],
            [KeyboardButton(text="За определенный период")]
        ],
        resize_keyboard=True
    )
    await message.answer("Выберите период поиска:", reply_markup=keyboard)
    await state.set_state(SearchSaleState.period_choice)

# Обрабатываем выбор периода
async def process_search_period(message: Message, state: FSMContext):
    user_data = await state.get_data()

    if message.text == "За все время":
        await generate_and_send_report(message, user_data['keywords'], None, None)
        await state.clear()
    elif message.text == "За определенный период":
        await message.answer("Введите период в формате YYYY-MM-DD - YYYY-MM-DD:")
        await state.set_state(SearchSaleState.date_range)
    else:
        await message.answer("Пожалуйста, выберите один из вариантов.")

# Обрабатываем ввод периода
async def process_search_date_range(message: Message, state: FSMContext):
    try:
        date_range = message.text.split(" - ")
        start_date, end_date = date_range[0], date_range[1]
        await state.update_data(start_date=start_date, end_date=end_date)

        user_data = await state.get_data()
        await generate_and_send_report(message, user_data['keywords'], start_date, end_date)
        await state.clear()
    except Exception:
        await message.answer("Неверный формат даты. Попробуйте еще раз.")

# Генерация и отправка отчета
async def generate_and_send_report(message: Message, keywords, start_date, end_date):
    # Фильтруем продажи по ключевым словам
    query = Sale.objects.all()
    for keyword in keywords:
        query = query.filter(Q(name__icontains=keyword))

    # Если выбран период, фильтруем по дате
    if start_date and end_date:
        query = query.filter(sale_date__range=[start_date, end_date])

    sales = query.order_by("sale_date")

    if not sales.exists():
        await message.answer("За указанный период продаж не найдено.")
        return

    # Генерация PDF-отчета
    pdf_path = generate_pdf_report(sales, start_date, end_date)
    await message.answer_document(types.FSInputFile(pdf_path), caption="Ваш отчет по продажам.")
