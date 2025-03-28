from aiogram import F, types
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import re
import os
from asgiref.sync import sync_to_async

# Регистрация шрифтов для русского языка
pdfmetrics.registerFont(TTFont('DejaVuSans', 'DejaVuSans.ttf'))
pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', 'DejaVuSans-Bold.ttf'))

class SearchSale(StatesGroup):
    waiting_for_query = State()
    waiting_for_period = State()
    waiting_for_query_with_period = State()

async def search_sale_start(message: Message, state: FSMContext):
    help_text = (
        "🔍 Введите ключевые слова для поиска фанеры (например: '12мм F/W')\n\n"
        "Поиск учитывает все введенные слова, но не их порядок. "
        "Регистр букв не имеет значения."
    )
    await message.answer(help_text)
    await state.set_state(SearchSale.waiting_for_query)

async def process_search_query(message: Message, state: FSMContext):
    search_query = message.text.lower()
    await state.update_data(search_query=search_query)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="За все время", callback_data="all_time")],
        [InlineKeyboardButton(text="За определенный период", callback_data="specific_period")]
    ])

    await message.answer(
        "Выберите период для поиска:",
        reply_markup=keyboard
    )

async def handle_period_choice(callback: types.CallbackQuery, state: FSMContext):
    if callback.data == "specific_period":
        await callback.message.answer(
            "Введите период в формате:\n"
            "YYYY-MM-DD - YYYY-MM-DD\n\n"
            "Например: 2025-03-01 - 2025-03-31"
        )
        await state.set_state(SearchSale.waiting_for_period)
    else:
        data = await state.get_data()
        search_query = data['search_query']
        await generate_and_send_report(callback.message, search_query)
        await state.clear()

    await callback.answer()

async def process_period_input(message: Message, state: FSMContext):
    try:
        date_from, date_to = map(str.strip, message.text.split('-'))
        date_from = datetime.strptime(date_from.strip(), "%Y-%m-%d").date()
        date_to = datetime.strptime(date_to.strip(), "%Y-%m-%d").date()

        await state.update_data(date_from=date_from, date_to=date_to)
        await message.answer(
            "Теперь повторно введите ключевые слова для поиска в выбранном периоде"
        )
        await state.set_state(SearchSale.waiting_for_query_with_period)
    except Exception as e:
        await message.answer(
            "Неправильный формат даты. Пожалуйста, введите период в формате:\n"
            "YYYY-MM-DD - YYYY-MM-DD\n\n"
            "Например: 2025-03-01 - 2025-03-31"
        )

async def process_query_with_period(message: Message, state: FSMContext):
    search_query = message.text.lower()
    data = await state.get_data()
    date_from = data['date_from']
    date_to = data['date_to']

    await generate_and_send_report(
        message,
        search_query,
        date_from=date_from,
        date_to=date_to
    )
    await state.clear()

@sync_to_async
def search_sales_in_db(search_query, date_from=None, date_to=None):
    from reports.models import Sale
    from django.db.models import Q, Sum

    # Разбиваем запрос на отдельные слова
    search_words = re.findall(r'\w+', search_query)

    # Создаем условия для поиска по каждому слову
    q_objects = Q()
    for word in search_words:
        q_objects &= Q(name__icontains=word)

    # Добавляем фильтр по дате если нужно
    if date_from and date_to:
        q_objects &= Q(sale_date__gte=date_from, sale_date__lte=date_to)

    # Получаем продажи с группировкой по месяцу и году
    sales = Sale.objects.filter(q_objects).order_by('sale_date')

    if not sales.exists():
        return None

    # Группируем продажи по месяцам
    grouped_sales = {}
    for sale in sales:
        month_year = sale.sale_date.strftime("%B %Y")
        if month_year not in grouped_sales:
            grouped_sales[month_year] = []
        grouped_sales[month_year].append(sale)

    return grouped_sales

async def generate_and_send_report(message, search_query, date_from=None, date_to=None):
    grouped_sales = await search_sales_in_db(search_query, date_from, date_to)

    if not grouped_sales:
        await message.answer(
            f"По запросу '{search_query}' не найдено продаж" +
            (f" за период с {date_from} по {date_to}" if date_from else "")
        )
        return

    # Создаем PDF отчет
    filename = f"sales_report_{datetime.now().timestamp()}.pdf"
    doc = SimpleDocTemplate(filename, pagesize=letter)
    styles = getSampleStyleSheet()
    styles['Title'].fontName = 'DejaVuSans-Bold'
    styles['Normal'].fontName = 'DejaVuSans'

    elements = []

    # Заголовок
    if date_from:
        title = f"Отчет по продажам '{search_query}'\nс {date_from} по {date_to}"
    else:
        title = f"Отчет по продажам '{search_query}' за все время"

    elements.append(Paragraph(title, styles['Title']))
    elements.append(Spacer(1, 12))

    # Подсчет общих сумм
    total_quantity = 0
    total_amount = 0
    payment_totals = {'cash': 0, 'card': 0, 'invoice': 0}

    # Добавляем данные по месяцам
    for month_year, sales in grouped_sales.items():
        elements.append(Paragraph(month_year, styles['Heading2']))

        for sale in sales:
            elements.append(Paragraph(
                f"{sale.name} - {sale.quantity} шт - {sale.total_price} руб - "
                f"{get_payment_method(sale.payment_method)} - {sale.sale_date.strftime('%d.%m.%Y')}",
                styles['Normal']
            ))

            # Считаем общие суммы
            total_quantity += sale.quantity
            total_amount += sale.total_price
            payment_totals[sale.payment_method] += sale.total_price

        elements.append(Spacer(1, 12))

    # Добавляем итоговую информацию
    elements.append(Paragraph("Итого:", styles['Heading2']))
    elements.append(Paragraph(f"Общее количество: {total_quantity} шт", styles['Normal']))
    elements.append(Paragraph(f"Общая сумма: {total_amount} руб", styles['Normal']))
    elements.append(Paragraph(
        f"Наличными: {payment_totals['cash']} руб | "
        f"Картой: {payment_totals['card']} руб | "
        f"По счету: {payment_totals['invoice']} руб",
        styles['Normal']
    ))

    doc.build(elements)

    # Отправляем файл
    file = FSInputFile(filename)
    await message.answer_document(
        file,
        caption=title
    )
    os.remove(filename)

def get_payment_method(method):
    methods = {
        'cash': 'Наличными',
        'card': 'Картой',
        'invoice': 'По счету'
    }
    return methods.get(method, method)
