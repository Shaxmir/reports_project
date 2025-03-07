# handlers/expense_handlers.py
import aiohttp
from datetime import datetime
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram import types, Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

router = Router()
API_URL = "http://185.255.133.33:8001/api/"

class ExpenseState(StatesGroup):
    reason = State()
    amount = State()
    comment = State()

async def start_expense(message: Message, state: FSMContext):
    await state.set_state(ExpenseState.reason)
    await message.answer("Введите причину расхода:")

async def process_reason(message: Message, state: FSMContext):
    await state.update_data(reason=message.text)
    await state.set_state(ExpenseState.amount)
    await message.answer("Введите сумму расхода:")

async def process_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text)
        await state.update_data(amount=amount)
        await state.set_state(ExpenseState.comment)
        await message.answer("Введите комментарий (можно пропустить):")
    except ValueError:
        await message.answer("Ошибка! Введите число.")

async def process_expense_comment(message: Message, state: FSMContext):
    data = await state.get_data()
    data["comment"] = message.text if message.text else ""
    data["date"] = datetime.now().strftime("%Y-%m-%d")
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{API_URL}expenses/", json=data) as resp:
            response_text = await resp.text()
            print("Ответ от сервера:", response_text)  # Логируем ответ!
            try:
                response_data = await resp.json()
            except Exception:
                response_data = {}
            if resp.status == 201:
                await message.answer("✅ Расход добавлен!")
            elif resp.status == 400 and "error" in response_data:
                await message.answer(f"⚠ Ошибка: {response_data['error']}")
            elif resp.status == 400:
                await message.answer("⚠ Ошибка: Недостаточно денег в кассе!")
            else:
                await message.answer(f"⚠ Ошибка! Код: {resp.status}")
    await state.clear()





# Получаем все расходы и создаем клавиатуру с кнопками
async def get_expenses_keyboard():
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_URL}expenses/") as resp:
            if resp.status == 200:
                expenses = await resp.json()
            else:
                return None

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=f"{exp['reason']}: {exp['amount']} руб.", callback_data="none"),
            ],
            [
                InlineKeyboardButton(text="📝 Изменить", callback_data=f"edit_{exp['id']}"),
                InlineKeyboardButton(text="❌ Удалить", callback_data=f"delete_{exp['id']}")
            ]
            for exp in expenses
        ]
    )
    return keyboard



# Хендлеры для изменения расходов


# Хендлер для команды /all_expenses
@router.message(Command("all_expenses"))
async def list_expenses(message: Message):
    keyboard = await get_expenses_keyboard()
    if keyboard:
        await message.answer("Ваши расходы:", reply_markup=keyboard)
    else:
        await message.answer("⚠ Ошибка! Не удалось загрузить расходы.")

# Хендлер для удаления расхода
@router.callback_query(F.data.startswith("delete_"))
async def delete_expense(callback: CallbackQuery):
    expense_id = callback.data.split("_")[1]
    
    async with aiohttp.ClientSession() as session:
        async with session.delete(f"{API_URL}expenses/{expense_id}/") as resp:
            if resp.status == 204:
                await callback.answer("Расход удален.")
                await callback.message.delete()
            else:
                await callback.answer("Ошибка при удалении!")

# Хендлер для изменения расхода (начало изменения)
@router.callback_query(F.data.startswith("edit_"))
async def edit_expense(callback: CallbackQuery):
    expense_id = callback.data.split("_")[1]
    await callback.message.answer(f"Введите новую сумму для расхода {expense_id}:")
    await callback.answer()

    @router.message()
    async def process_edit_expense(message: Message):
        new_amount = message.text.strip()
        if not new_amount.isdigit():
            await message.answer("Введите корректное число.")
            return
        
        async with aiohttp.ClientSession() as session:
            async with session.patch(f"{API_URL}expenses/{expense_id}/", json={"amount": new_amount}) as resp:
                if resp.status == 200:
                    await message.answer(f"✅ Расход обновлен: {new_amount} руб.")
                else:
                    await message.answer("⚠ Ошибка при обновлении!")
