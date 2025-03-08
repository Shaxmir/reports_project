from aiogram import types
from aiogram.filters import BaseFilter
from sales_reports.settings import CREATOR_ID, ADMIN_IDS

class IsAdmin(BaseFilter):
    async def __call__(self, message: types.Message) -> bool:
        user_id = message.from_user.id
        # Если пользователь — создатель, разрешаем доступ
        if user_id == CREATOR_ID:
            return True
        # Если пользователь — администратор, разрешаем доступ
        if user_id in ADMIN_IDS:
            return True
        # Если пользователь не имеет прав, отправляем сообщение
        await message.answer("🚫 У вас нет прав администратора.\nЧтобы получить права свяжитесь с @shaxsodo")
        return False

class IsCreator(BaseFilter):
    async def __call__(self, message: types.Message) -> bool:
        if message.from_user.id != CREATOR_ID:
            await message.answer("🚫 У вас нет прав для выполнения этой команды.\nЧтобы получить права свяжитесь с @shaxsodo")
            return False
        return True
