import os
import calendar
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import Message, FSInputFile, CallbackQuery
from asgiref.sync import sync_to_async

# Подключаем шрифт для поддержки кириллицы
pdfmetrics.registerFont(TTFont('DejaVuSans', 'DejaVuSans.ttf'))
pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', 'DejaVuSans-Bold.ttf'))
# Клавиатура выбора года
async def create_year_selector():
    keyboard = InlineKeyboardBuilder()
    now = datetime.now()
    for year in range(now.year - 1, now.year + 2):  # Добавляем прошлый, текущий и следующий годы
        keyboard.button(text=str(year), callback_data=f"year_{year}")
    return keyboard.as_markup()

# Клавиатура выбора месяца
async def create_month_selector(year: int):
    keyboard = InlineKeyboardBuilder()
    months_dict = {
    "January": "Январь",
    "February": "Февраль",
    "March": "Март",
    "April": "Апрель",
    "May": "Май",
    "June": "Июнь",
    "July": "Июль",
    "August": "Август",
    "September": "Сентябрь",
    "October": "Октябрь",
    "November": "Ноябрь",
    "December": "Декабрь"
    }

    for i, month in enumerate(calendar.month_name[1:], start=1):
        keyboard.button(text=months_dict[month], callback_data=f"month_{i}_{year}")
    keyboard.adjust()
    return keyboard.as_markup()

# Генерация PDF отчета
async def generate_monthly_report(month: int, year: int):
    filename = f"monthly_report_{month}_{year}.pdf"
    doc = SimpleDocTemplate(filename, pagesize=letter)
    styles = getSampleStyleSheet()
    
    # Создаем новый уникальный стиль
    styles.add(ParagraphStyle(name='CustomTitle', fontName='DejaVuSans-Bold', fontSize=16, alignment=1, leading=100))
    styles.add(ParagraphStyle(name='Russian', fontName='DejaVuSans', fontSize=12, leading=30))

    elements = []
    month_name = calendar.month_name[month]
    
    # Используем новый стиль для заголовка
    elements.append(Paragraph(f"Отчет за {month_name} {year}", styles['CustomTitle']))

    sales_data = await get_monthly_sales(month, year)
    expenses_data = await get_monthly_expenses(month, year)

    if not sales_data and not expenses_data:
        elements.append(Paragraph("В этом месяце не было продаж или расходов.", styles['Russian']))
        doc.build(elements)
        return filename

    # Формируем таблицу
    data = [["Дата", "Общая сумма", "Наличные", "Карта", "Счет", "Расходы"]]
    total_sales = {'total': 0, 'cash': 0, 'card': 0, 'invoice': 0}
    total_expenses = 0

    for day in sorted(set(sales_data.keys()) | set(expenses_data.keys())):
        day_sales = sales_data.get(day, {})
        day_expenses = expenses_data.get(day, 0)

        total_sales['total'] += day_sales.get('total', 0)
        total_sales['cash'] += day_sales.get('cash', 0)
        total_sales['card'] += day_sales.get('card', 0)
        total_sales['invoice'] += day_sales.get('invoice', 0)
        total_expenses += day_expenses

        data.append([ 
            day.strftime("%Y-%m-%d"),
            f"{day_sales.get('total', 0):,.0f} p.",
            f"{day_sales.get('cash', 0):,.0f} p.",
            f"{day_sales.get('card', 0):,.0f} p.",
            f"{day_sales.get('invoice', 0):,.0f} p.",
            f"{day_expenses:,.0f} p." if day_expenses else "-"
        ])

    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),  # Фон для заголовков
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),  # Цвет текста в заголовках
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # Выравнивание текста по центру
        ('FONTNAME', (0, 0), (-1, 0), 'DejaVuSans'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),  # Фон для данных
        ('GRID', (0, 0), (-1, -1), 1, colors.black),  # Толщина и цвет линии сетки
        ('LINEABOVE', (0, 0), (-1, 0), 2, colors.black),  # Линии над заголовками
        ('LINEBELOW', (0, 0), (-1, -1), 1, colors.black),  # Линии под таблицей
        ('LINEBEFORE', (0, 0), (0, -1), 5, colors.black),  # Линии перед первым столбцом
        ('LINEAFTER', (0, 0), (0, -1), 5, colors.black),  # Линии после последнего столбца
    ]))

    elements.append(table)

    # Общие суммы, красиво отформатированы
    elements.append(Paragraph(f"Общая сумма продаж: {total_sales['total']:,.0f} руб.", styles['Russian']))
    elements.append(Paragraph(
        f"Наличными: {total_sales['cash']:,.0f} руб. | Картой: {total_sales['card']:,.0f} руб. | По счету: {total_sales['invoice']:,.0f} руб.",
        styles['Russian']
    ))
    elements.append(Paragraph(f"Общая сумма расходов: {total_expenses:,.0f} руб.", styles['Russian']))

    doc.build(elements)
    return filename

# Получение данных из БД
@sync_to_async
def get_monthly_sales(month: int, year: int):
    from reports.models import Sale
    from django.db.models import Sum, Q
    from collections import defaultdict

    sales = Sale.objects.filter(sale_date__month=month, sale_date__year=year).values('sale_date').annotate(
        total=Sum('total_price'),
        cash=Sum('total_price', filter=Q(payment_method='cash')),
        card=Sum('total_price', filter=Q(payment_method='card')),
        invoice=Sum('total_price', filter=Q(payment_method='invoice'))
    )

    result = defaultdict(dict)
    for s in sales:
        date = s['sale_date']
        result[date] = {
            'total': s['total'] or 0,
            'cash': s['cash'] or 0,
            'card': s['card'] or 0,
            'invoice': s['invoice'] or 0
        }
    return result

@sync_to_async
def get_monthly_expenses(month: int, year: int):
    from reports.models import Expense
    from django.db.models import Sum
    from collections import defaultdict

    expenses = Expense.objects.filter(date__month=month, date__year=year).values('date').annotate(total=Sum('amount'))
    return {e['date']: e['total'] for e in expenses}

# Хендлеры
async def monthly_report_start(message: Message):
    await message.answer("Выберите год для отчета:", reply_markup=await create_year_selector())

async def handle_year_selection(callback: CallbackQuery):
    _, year = callback.data.split('_')
    print('CallBack year - ',callback.data.split('_'))
    year = int(year)
    await callback.message.edit_text(f"Выбран год {year}. Теперь выберите месяц:", reply_markup=await create_month_selector(year))

async def handle_month_selection(callback: CallbackQuery):
    _, month, year = callback.data.split('_')
    print('CallBack month - ',callback.data.split('_'))
    month = int(month)
    year = int(year)

    await callback.answer(f"Формируем отчет за {calendar.month_name[month]} {year}...")

    try:
        filename = await generate_monthly_report(month, year)
        file = FSInputFile(filename)
        await callback.message.answer_document(file, caption=f"Отчет за {calendar.month_name[month]} {year}")
        os.remove(filename)
    except Exception as e:
        await callback.message.answer(f"Ошибка при формировании отчета: {str(e)}")
