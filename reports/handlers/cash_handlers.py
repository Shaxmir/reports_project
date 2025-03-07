# handlers/cash_handlers.py
import aiohttp
from aiogram import types
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

API_URL = "http://185.255.133.33:8001/api/"

class CashState(StatesGroup):
    amount = State()

async def start_cash(message: Message, state: FSMContext):
    await state.set_state(CashState.amount)
    await message.answer("Введите сумму, которую хотите добавить в кассу:\n(Если сумма с копейками, используйте точку '.')")

async def process_cash(message: Message, state: FSMContext):
    try:
        cash_addition = float(message.text)
        if cash_addition <= 0:
            await message.answer("Ошибка! Сумма пополнения должна быть положительной.")
            return
        data = {"amount": cash_addition}
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{API_URL}cash/", json=data) as resp:
                if resp.status == 201:
                    await message.answer(f"✅ В кассу добавлено {cash_addition} рублей!")
                else:
                    error_text = await resp.text()
                    await message.answer(f"⚠ Ошибка при пополнении кассы! Код: {resp.status}. Текст ошибки: {error_text}")
        await state.clear()
    except ValueError:
        await message.answer("Ошибка! Введите число.")
    except Exception as e:
        await message.answer(f"Произошла ошибка: {str(e)}")
