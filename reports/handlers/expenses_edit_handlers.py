from aiogram import types
from aiogram.filters import Command
import aiohttp
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery
from asgiref.sync import sync_to_async
from datetime import date
from reports.models import Expense

API_URL = "http://127.0.0.1:8000/api/expenses/"

# Определяем состояние для редактирования
class EditExpenseState(StatesGroup):
    amount = State()
    comment = State()

@sync_to_async
def get_today_expenses():
    """Получает список расходов за сегодня"""
    return list(Expense.objects.filter(date=date.today()))

async def get_expenses(message: types.Message):
    """Вывод списка расходов за сегодня с кнопками редактирования"""
    expenses = await get_today_expenses()

    if not expenses:
        await message.answer("❌ Расходов сегодня не было.")
        return

    # Для каждого расхода отправляем отдельное сообщение
    for expense in expenses:
        expense_text = (
            f"📌 *{expense.reason}*\n"
            f"   - Сумма: {expense.amount} руб.\n"
            f"   - Комментарий: {expense.comment if expense.comment else 'Нет'}\n"
            f"-"
        )

        keyboard = InlineKeyboardBuilder()

        # Добавляем кнопки "Удалить" и "Изменить" для каждого расхода
        keyboard.button(text="❌ Удалить", callback_data=f"delete_expense_{expense.id}")
        keyboard.button(text="✏ Изменить", callback_data=f"edit_expense_{expense.id}")

        # Отправляем сообщение с расходом и кнопками
        await message.answer(expense_text, reply_markup=keyboard.as_markup())


async def delete_expense(expense_id: int):
    """Удаление расхода через API"""
    async with aiohttp.ClientSession() as session:
        async with session.delete(f"{API_URL}{expense_id}/") as resp:
            return resp.status == 204

# Определяем состояния для редактирования
class EditExpenseState(StatesGroup):
    amount = State()
    comment = State()
    reason = State()  # Добавляем состояние для редактирования причины

async def edit_expense_start(callback: CallbackQuery, state: FSMContext):
    """Запрос новой суммы расхода"""
    expense_id = callback.data.split("_")[-1]
    await state.update_data(expense_id=expense_id)
    await state.set_state(EditExpenseState.amount)
    await callback.message.answer("Введите новую сумму расхода:")

async def edit_expense_amount(message: types.Message, state: FSMContext):
    """Сохранение новой суммы и запрос нового комментария"""
    try:
        amount = float(message.text)
        await state.update_data(amount=amount)
        await state.set_state(EditExpenseState.comment)
        await message.answer("Введите новый комментарий (можно пропустить):")
    except ValueError:
        await message.answer("Ошибка! Введите число.")

async def edit_expense_comment(message: types.Message, state: FSMContext):
    """Сохранение нового комментария и запрос новой причины"""
    data = await state.get_data()
    expense_id = data["expense_id"]
    new_amount = data["amount"]
    new_comment = message.text if message.text else ""

    # Сохраняем комментарий
    await state.update_data(comment=new_comment)

    # Переходим к вводу причины
    await state.set_state(EditExpenseState.reason)
    await message.answer("Введите новую причину расхода:")

# Вводим исправление в функцию edit_expense_reason
async def edit_expense_reason(message: types.Message, state: FSMContext):
    """Отправка обновленных данных о расходе, включая причину"""
    data = await state.get_data()
    expense_id = data["expense_id"]
    new_amount = data["amount"]
    new_comment = data["comment"]
    new_reason = message.text if message.text else ""  # Получаем причину из сообщения

    # Получаем текущую дату в нужном формате (YYYY-MM-DD)
    current_date = data.get("date", date.today().strftime("%Y-%m-%d"))  # Сохраняем старую дату или текущую, если не задана

    # Обновляем данные
    update_data = {
        "amount": new_amount,
        "comment": new_comment,
        "reason": new_reason,
        "date": current_date,  # Передаем дату в правильном формате
    }

    async with aiohttp.ClientSession() as session:
        async with session.put(f"{API_URL}{expense_id}/", json=update_data) as resp:
            response_text = await resp.text()  # Получаем текст ответа сервера

            if resp.status == 200:
                await message.answer("✅ Расход обновлён!")
            else:
                await message.answer(f"⚠ Ошибка при обновлении. Код: {resp.status}\nОтвет: {response_text}")

    await state.clear()


async def delete_expense_callback(callback: CallbackQuery):
    """Обработчик кнопки удаления расхода"""
    expense_id = int(callback.data.split("_")[-1])
    success = await delete_expense(expense_id)
    if success:
        await callback.answer("✅ Расход удален!")
        await callback.message.delete()
    else:
        await callback.answer("⚠ Ошибка при удалении.")

async def edit_expense_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки изменения расхода"""
    expense_id = int(callback.data.split("_")[-1])
    await state.update_data(expense_id=expense_id)
    await state.set_state(EditExpenseState.amount)
    await callback.message.answer("✏ Введите новую сумму для расхода:")
