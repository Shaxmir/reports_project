from aiogram import types
from aiogram.filters import Command
from aiogram.utils.markdown import hbold
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from django.db.models import Q
from reports.models import Sale
from datetime import datetime
import asyncio
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from functools import reduce
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup




# Определение состояний FSM
class SearchState(StatesGroup):
    query = State()  # Состояние для хранения запроса пользователя
    start_date = State()  # Состояние для хранения даты начала
    end_date = State()  # Состояние для хранения даты конца


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


async def search_sale_handler(message: types.Message):
    await message.answer("Введите ключевые слова для поиска фанеры (например, '12мм F/W'):")
    await asyncio.sleep(1)  # Подождем ввода


async def process_search_query(message: types.Message, state: FSMContext):
    query = message.text.strip()
    words = query.lower().split()

    if len(words) < 1:
        await message.answer("Пожалуйста, введите хотя бы одно ключевое слово для поиска.")
        return

    # Сохраняем ключевые слова в состоянии
    await state.update_data(query=query)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="За все время", callback_data=f"search_all:{query}")],
            [InlineKeyboardButton(text="За определенный период", callback_data=f"search_period:{query}")]
        ]
    )

    await message.answer("Выберите период:", reply_markup=keyboard)


async def process_search_callback(callback: types.CallbackQuery, state: FSMContext):
    action, query = callback.data.split(":", 1)
    words = query.lower().split()

    if action == "search_all":
        # Фильтрация с использованием всех ключевых слов
        sales = Sale.objects.filter(
            reduce(lambda q, word: q & Q(name__icontains=word), [Q()] + [Q(name__icontains=word) for word in words])
        )

        if not sales.exists():
            await callback.message.answer("Продажи с такими параметрами не найдены.")
            return

        pdf_data = generate_pdf_report(sales)
        await callback.message.answer_document(types.BufferedInputFile(pdf_data, filename="sales_report.pdf"))

    elif action == "search_period":
        await callback.message.answer("Введите период в формате YYYY-MM-DD - YYYY-MM-DD")


async def process_period_input(message: types.Message, state: FSMContext):
    try:
        period = message.text.strip()
        start_date, end_date = map(str.strip, period.split("-"))
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
        end_date = datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        await message.answer("Некорректный формат. Введите даты в формате YYYY-MM-DD - YYYY-MM-DD")
        return

    await message.answer("Теперь введите ключевые слова для поиска фанеры:")
    # Сохраняем временные данные о периоде в состоянии
    await message.answer("Введите ключевые слова для поиска фанеры:")
    await state.update_data(start_date=start_date, end_date=end_date)


async def process_period_search(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    if 'start_date' not in user_data or 'end_date' not in user_data:
        await message.answer("Сначала введите период поиска.")
        return

    start_date, end_date = user_data['start_date'], user_data['end_date']
    query = message.text.strip()
    words = query.lower().split()

    # Фильтрация с использованием всех ключевых слов и указанного периода
    sales = Sale.objects.filter(
        reduce(lambda q, word: q & Q(name__icontains=word), [Q()] + [Q(name__icontains=word) for word in words]),
        sale_date__range=(start_date, end_date)
    )

    if not sales.exists():
        await message.answer("Продажи с такими параметрами за указанный период не найдены.")
        return

    pdf_data = generate_pdf_report(sales, start_date, end_date)
    await message.answer_document(types.BufferedInputFile(pdf_data, filename="sales_report.pdf"))
