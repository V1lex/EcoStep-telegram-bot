from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def get_main_menu():
    """Главное меню с кнопками"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📋 Задания"),
                KeyboardButton(text="📮 Отчёт")
            ],
            [
                KeyboardButton(text="📈 Прогресс"),
                KeyboardButton(text="❓ Помощь")
            ]
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие"
    )
    return keyboard

def get_back_button():
    """Кнопка возврата в главное меню"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🏠 Главное меню")]
        ],
        resize_keyboard=True
    )
    return keyboard

def get_tasks_keyboard():
    """Inline-клавиатура со списком заданий"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚰 Отказаться от одноразовой бутылки (5 баллов)", callback_data="task_1")],
            [InlineKeyboardButton(text="🚶 Пойти пешком до учёбы (10 баллов)", callback_data="task_2")],
            [InlineKeyboardButton(text="📄 Сдать макулатуру (15 баллов)", callback_data="task_3")],
            [InlineKeyboardButton(text="♻️ Использовать многоразовую сумку (5 баллов)", callback_data="task_4")],
            [InlineKeyboardButton(text="💡 Выключить свет на час (7 баллов)", callback_data="task_5")]
        ]
    )
    return keyboard
