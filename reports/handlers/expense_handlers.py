# handlers/expense_handlers.py
import aiohttp
from datetime import datetime
from aiogram import types
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

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
