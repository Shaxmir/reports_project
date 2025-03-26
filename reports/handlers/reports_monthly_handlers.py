import os
import calendar
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import Message, FSInputFile, CallbackQuery
from asgiref.sync import sync_to_async

# Клавиатура для выбора месяца/года
async def create_month_selector():
    now = datetime.now()
    keyboard = InlineKeyboardBuilder()

    # Кнопки месяцев
    for i, month in enumerate(calendar.month_name[1:], start=1):
        keyboard.button(text=month, callback_data=f"month_{i}_{now.year}")

    # Кнопки годов (текущий и предыдущий)
    keyboard.button(text=str(now.year - 1), callback_data=f"year_{now.year - 1}")
    keyboard.button(text=str(now.year), callback_data=f"year_{now.year}")

    return keyboard.as_markup()

# Генерация PDF отчета
async def generate_monthly_report(month: int, year: int):
    filename = f"monthly_report_{month}_{year}.pdf"
    doc = SimpleDocTemplate(filename, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []
    
    # Заголовок
    month_name = calendar.month_name[month]
    elements.append(Paragraph(f"Отчет за {month_name} {year}", styles['Title']))
    
    # Получаем данные из БД
    sales_data = await get_monthly_sales(month, year)
    expenses_data = await get_monthly_expenses(month, year)
    
    # Формируем данные для таблицы
    data = [["Дата", "Общая сумма", "Наличные", "Карта", "Счет", "Расходы"]]
    
    total_sales = {
        'total': 0,
        'cash': 0,
        'card': 0,
        'invoice': 0
    }
    total_expenses = 0
    
    for day in sorted(set(sales_data.keys()) | set(expenses_data.keys())):
        day_sales = sales_data.get(day, {})
        day_expenses = expenses_data.get(day, 0)
        
        # Суммируем общие значения
        total_sales['total'] += day_sales.get('total', 0)
        total_sales['cash'] += day_sales.get('cash', 0)
        total_sales['card'] += day_sales.get('card', 0)
        total_sales['invoice'] += day_sales.get('invoice', 0)
        total_expenses += day_expenses
        
        # Добавляем строку в таблицу
        data.append([
            day.strftime("%Y-%m-%d"),
            f"{day_sales.get('total', 0):,} руб.",
            f"{day_sales.get('cash', 0):,} руб.",
            f"{day_sales.get('card', 0):,} руб.",
            f"{day_sales.get('invoice', 0):,} руб.",
            f"{day_expenses:,} руб." if day_expenses else "-"
        ])
    
    # Создаем таблицу
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(table)
    
    # Итоговые значения
    elements.append(Paragraph("<br/><b>Итого:</b>", styles['Normal']))
    elements.append(Paragraph(
        f"Общая сумма продаж за {month_name}: {total_sales['total']:,} руб.", 
        styles['Normal']
    ))
    elements.append(Paragraph(
        f"Наличными: {total_sales['cash']:,} руб. | "
        f"Картой: {total_sales['card']:,} руб. | "
        f"По счету: {total_sales['invoice']:,} руб.",
        styles['Normal']
    ))
    elements.append(Paragraph(
        f"Общая сумма расходов за {month_name}: {total_expenses:,} руб.",
        styles['Normal']
    ))
    
    doc.build(elements)
    return filename

# Получение данных из БД
@sync_to_async
def get_monthly_sales(month: int, year: int):
    from reports.models import Sale
    from django.db.models import Sum, Q
    from collections import defaultdict
    
    sales = Sale.objects.filter(
        sale_date__month=month,
        sale_date__year=year
    ).values('sale_date').annotate(
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
    
    expenses = Expense.objects.filter(
        date__month=month,
        date__year=year
    ).values('date').annotate(
        total=Sum('amount')
    )
    
    return {e['date']: e['total'] for e in expenses}

# Хендлеры
async def monthly_report_start(message: Message):
    await message.answer(
        "Выберите месяц и год для отчета:",
        reply_markup=await create_month_selector()
    )

async def handle_month_selection(callback: CallbackQuery):
    _, month, year = callback.data.split('_')
    month = int(month)
    year = int(year)
    
    await callback.answer(f"Формируем отчет за {calendar.month_name[month]} {year}...")
    
    try:
        filename = await generate_monthly_report(month, year)
        file = FSInputFile(filename)
        await callback.message.answer_document(
            file,
            caption=f"Отчет за {calendar.month_name[month]} {year}"
        )
        os.remove(filename)
    except Exception as e:
        await callback.message.answer(f"Ошибка при формировании отчета: {str(e)}")