# handlers/sale_handlers.py
import aiohttp
import aiogram
from datetime import date
from aiogram import types
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from asgiref.sync import sync_to_async
from reports.models import Sale, CashRegister

# Определяем состояния для продажи
class SaleState(StatesGroup):
    name = State()
    quantity = State()
    price = State()
    payment_method = State()
    sale_date = State()
    shipment_date = State()
    comment = State()

API_URL = "http://185.255.133.33:8001/api/"

# Обработчик команды /sale
async def start_sale(message: Message, state: FSMContext):
    await state.set_state(SaleState.name)
    await message.answer("Введите название фанеры:")

async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(SaleState.quantity)
    await message.answer("Введите количество проданных единиц:")

async def process_quantity(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Ошибка! Введите число.")
        return
    await state.update_data(quantity=int(message.text))
    await state.set_state(SaleState.price)
    await message.answer("Введите цену за единицу:")

async def process_price(message: Message, state: FSMContext):
    try:
        price = float(message.text)
        await state.update_data(price_per_unit=price)
        await state.set_state(SaleState.payment_method)
        await message.answer("Выберите способ оплаты: invoice, card, cash")
    except ValueError:
        await message.answer("Ошибка! Введите число.")

async def process_payment(message: Message, state: FSMContext):
    if message.text not in ["invoice", "card", "cash"]:
        await message.answer("Ошибка! Введите: invoice, card или cash")
        return
    await state.update_data(payment_method=message.text)
    await state.set_state(SaleState.sale_date)
    await message.answer("Введите дату продажи (YYYY-MM-DD):")

async def process_sale_date(message: Message, state: FSMContext):
    await state.update_data(sale_date=message.text)
    await state.set_state(SaleState.shipment_date)
    await message.answer("Введите дату отгрузки (YYYY-MM-DD):")

async def process_shipment_date(message: Message, state: FSMContext):
    await state.update_data(shipment_date=message.text)
    await state.set_state(SaleState.comment)
    await message.answer("Введите комментарий (можно пропустить):")

async def process_comment(message: Message, state: FSMContext):
    data = await state.get_data()
    data["comment"] = message.text if message.text else ""
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{API_URL}sales/", json=data) as resp:
            if resp.status == 201:
                await message.answer("✅ Продажа добавлена!")
                if data["payment_method"] == "cash":
                    sale_amount = data["quantity"] * data["price_per_unit"]
                    cash_data = {"amount": sale_amount}
                    async with session.post(f"{API_URL}cash/", json=cash_data) as cash_resp:
                        response_data = await cash_resp.json()
                        if "cash_total" in response_data:
                            new_balance = response_data["cash_total"]
                            await message.answer(
                                f"💰 Касса пополнена на {sale_amount} руб.\n🔹 Новый остаток: {new_balance} руб."
                            )
                        else:
                            await message.answer(f"⚠ Ошибка при обновлении кассы: {response_data}")
            else:
                error_text = await resp.text()
                await message.answer(f"⚠ Ошибка при добавлении продажи: {error_text}")
    await state.clear()

@sync_to_async
def get_today_sales():
    return list(Sale.objects.filter(sale_date=date.today()))

# Функция для отправки сообщений по частям
async def send_long_message(message, text, chunk_size=4096):
    # Разбиваем текст на части, если его длина превышает лимит
    for i in range(0, len(text), chunk_size):
        try:
            await message.answer(text[i:i+chunk_size], parse_mode="Markdown")
        except aiogram.exceptions.TelegramBadRequest as e:
            if "can't parse entities" in str(e):
                # Если ошибка из-за разметки, пробуем очистить текст от неверных символов
                await message.answer(text[i:i+chunk_size], parse_mode="HTML")
            else:
                # В случае других ошибок выводим сообщение об ошибке
                await message.answer("Произошла ошибка при отправке сообщения.")
                break



async def get_all_sales(message: types.Message):
    sales = await get_today_sales()  # Получаем только сегодняшние продажи

    if not sales:
        await message.answer("❌ Продаж сегодня не было.")
        return

    sales_list = []
    unique_sales = set()  # Для предотвращения дублирования продаж

    for sale in sales:
        if sale.id in unique_sales:
            continue  # Если продажа уже была, пропускаем
        unique_sales.add(sale.id)

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
            "-"
        )
        sales_list.append(sale_info)

    report_text = "📋 *Список всех продаж за сегодня:*\n\n" + "\n".join(sales_list)
    print(sale_info)
    await send_long_message(message, report_text)
