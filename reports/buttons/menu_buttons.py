from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Кнопки отчётов
report_buttons = [
    KeyboardButton(text="📊 Отчет за сегодня"),
    KeyboardButton(text="💰 Продажи на сегодня"),
]

# Кнопки для поиска и экспорта
report_pdf_buttons = [
    KeyboardButton(text="📄 Отчет в PDF"),
    KeyboardButton(text="📅 Старые отчеты"),
    KeyboardButton(text="📆 Отчеты за месяц"),
]

search_buttons = [
    KeyboardButton(text="🔎 Поиск по дате"),
    KeyboardButton(text="🔎 Поиск подробный"),
]

# Админские кнопки
admin_buttons = [
    KeyboardButton(text="➕ Продажа"),
    KeyboardButton(text="➕ Расход"),
    KeyboardButton(text="➕ В кассу"),
    KeyboardButton(text="✏️ Ред. расход"),
    KeyboardButton(text="✏️ Ред. продажу"),
]

# Создание клавиатуры
keyboard = ReplyKeyboardMarkup(
    keyboard=[report_buttons, report_pdf_buttons, search_buttons, admin_buttons],
    resize_keyboard=True  # Делает кнопки компактными
)