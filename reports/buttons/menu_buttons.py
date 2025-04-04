from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Кнопки отчётов
report_buttons = [
    KeyboardButton(text="📊 Отчет за сегодня"),
    KeyboardButton(text="📅 Старые отчеты"),
    KeyboardButton(text="📆 Отчеты за месяц"),
]

# Кнопки для поиска и экспорта
search_buttons = [
    KeyboardButton(text="🔎 Поиск продаж/расходов"),
    KeyboardButton(text="📄 Отчет в PDF"),
    KeyboardButton(text="💰 Продажи на сегодня"),
]

# Админские кнопки
admin_buttons = [
    KeyboardButton(text="➕ Добавить продажу"),
    KeyboardButton(text="💸 Добавить расход"),
    KeyboardButton(text="💵 Обновить кассу"),
    KeyboardButton(text="✏️ Редактировать расход"),
    KeyboardButton(text="📝 Редактировать продажу"),
]

# Создание клавиатуры
keyboard = ReplyKeyboardMarkup(
    keyboard=[report_buttons, search_buttons, admin_buttons],
    resize_keyboard=True  # Делает кнопки компактными
)