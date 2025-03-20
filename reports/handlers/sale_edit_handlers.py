from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import aiohttp
import aiogram
from datetime import date
from aiogram import types
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from asgiref.sync import sync_to_async
from reports.models import Sale, CashRegister
from decimal import Decimal

@sync_to_async
def get_today_sales():
    return list(Sale.objects.filter(sale_date=date.today()))

async def get_all_sales(message: types.Message):
    sales = await get_today_sales()  # Получаем только сегодняшние продажи

    if not sales:
        await message.answer("❌ Продаж сегодня не было.")
        return

    # Создаем список кнопок
    buttons = []
    for sale in sales:
        button = InlineKeyboardButton(text=sale.name, callback_data=f"sale_{sale.id}")
        buttons.append([button])  # Каждая кнопка должна быть в отдельном списке

    # Создаем клавиатуру с кнопками
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons, row_width=1)

    await message.answer("📋 Список всех продаж за сегодня:", reply_markup=keyboard)




async def show_sale_info(callback_query: types.CallbackQuery):
    sale_id = int(callback_query.data.split("_")[1])
    sale = await sync_to_async(Sale.objects.get)(id=sale_id)

    payment_method = {
        'invoice': 'По счету',
        'card': 'Картой',
        'cash': 'Наличными'
    }.get(sale.payment_method, 'Неизвестно')

    sale_info = (
        f"🪚 *{sale.name}*\n"
        f"   - Количество: {sale.quantity} шт.\n"
        f"   - Цена за единицу: {sale.price_per_unit} руб.\n"
        f"   - Общая сумма: {sale.total_price} руб.\n"
        f"   - Способ оплаты: {payment_method}\n"
        f"   - Дата продажи: {sale.sale_date}\n"
        f"   - Дата отгрузки: {sale.shipment_date}\n"
        f"   - Комментарий: {sale.comment if sale.comment else 'Нет'}\n"
    )

    # Создаем кнопки
    buttons = [
        InlineKeyboardButton(text="Удалить", callback_data=f"delete_sale_{sale.id}"),
        InlineKeyboardButton(text="Изменить", callback_data=f"edit_sale_{sale.id}")
    ]

    # Создаем клавиатуру с кнопками
    keyboard = InlineKeyboardMarkup(inline_keyboard=[buttons], row_width=2)

    await callback_query.message.answer(sale_info, reply_markup=keyboard)

async def delete_sale(callback_query: CallbackQuery):
    sale_id = int(callback_query.data.split("_")[2])
    sale = await sync_to_async(Sale.objects.get)(id=sale_id)

    if sale.payment_method == "cash":
        # Ищем запись в кассе за сегодня
        cash_register, created = await sync_to_async(CashRegister.objects.get_or_create)(
            date=date.today(),
            defaults={"cash_total": Decimal('0.00')}  # Значение по умолчанию, если запись не найдена
        )
        # Вычитаем сумму из кассы
        cash_register.cash_total -= sale.total_price
        # Защита от отрицательных значений
        cash_register.cash_total = max(Decimal('0.00'), cash_register.cash_total)
        await sync_to_async(cash_register.save)()

    await sync_to_async(sale.delete)()
    await callback_query.message.answer("✅ Продажа удалена!")


class EditSaleState(StatesGroup):
    name = State()
    quantity = State()
    price = State()
    payment_method = State()
    comment = State()

async def start_edit_sale(callback_query: CallbackQuery, state: FSMContext):
    sale_id = int(callback_query.data.split("_")[2])
    await state.update_data(sale_id=sale_id)
    await state.set_state(EditSaleState.name)
    await callback_query.message.answer("Введите новое название фанеры:")

async def process_edit_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(EditSaleState.quantity)
    await message.answer("Введите новое количество проданных единиц:")

async def process_edit_quantity(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Ошибка! Введите число.")
        return
    await state.update_data(quantity=int(message.text))
    await state.set_state(EditSaleState.price)
    await message.answer("Введите новую цену за единицу:")

async def process_edit_price(message: Message, state: FSMContext):
    try:
        price = float(message.text)
        await state.update_data(price_per_unit=price)
        await state.set_state(EditSaleState.payment_method)
        await message.answer("Выберите новый способ оплаты: invoice, card, cash")
    except ValueError:
        await message.answer("Ошибка! Введите число.")

async def process_edit_payment(message: Message, state: FSMContext):
    if message.text not in ["invoice", "card", "cash"]:
        await message.answer("Ошибка! Введите: invoice, card или cash")
        return
    await state.update_data(payment_method=message.text)
    await state.set_state(EditSaleState.comment)
    await message.answer("Введите новый комментарий (можно пропустить):")

async def process_edit_comment(message: Message, state: FSMContext):
    data = await state.get_data()
    data["comment"] = message.text if message.text else ""
    sale_id = data.pop("sale_id")
    sale = await sync_to_async(Sale.objects.get)(id=sale_id)

    # Приводим все значения к типу Decimal
    old_total_price = Decimal(str(sale.total_price))  # Приводим к Decimal
    sale.total_price = Decimal(str(sale.quantity * sale.price_per_unit))  # Приводим к Decimal

    old_payment_method = sale.payment_method

    # Обновляем поля продажи
    for key, value in data.items():
        setattr(sale, key, value)
    await sync_to_async(sale.save)()

   # Обновляем кассу, если оплата была наличными
    if old_payment_method == "cash" and sale.payment_method == "cash":
        # Ищем запись в кассе за сегодня
        cash_register, created = await sync_to_async(CashRegister.objects.get_or_create)(
            date=date.today(),
            defaults={"cash_total": Decimal('0.00')}  # Значение по умолчанию, если запись не найдена
        )
        if sale.total_price > old_total_price:
            cash_register.cash_total += Decimal(str(sale.total_price)) - old_total_price
        else:
            cash_register.cash_total -= old_total_price - Decimal(str(sale.total_price))
        await sync_to_async(cash_register.save)()

    elif old_payment_method == "cash" and sale.payment_method != "cash":
        # Ищем запись в кассе за сегодня
        cash_register, created = await sync_to_async(CashRegister.objects.get_or_create)(
            date=date.today(),
            defaults={"cash_total": Decimal('0.00')}
        )
        cash_register.cash_total -= old_total_price
        await sync_to_async(cash_register.save)()

    elif old_payment_method != "cash" and sale.payment_method == "cash":
        # Ищем запись в кассе за сегодня
        cash_register, created = await sync_to_async(CashRegister.objects.get_or_create)(
            date=date.today(),
            defaults={"cash_total": Decimal('0.00')}
        )
        cash_register.cash_total += Decimal(str(sale.total_price))
        await sync_to_async(cash_register.save)()

    await message.answer("✅ Продажа изменена!")
    await state.clear()
