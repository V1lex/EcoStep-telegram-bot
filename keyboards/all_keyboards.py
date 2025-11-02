from collections.abc import Iterable, Sequence

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)


def get_main_menu():
    """Главное меню с кнопками."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📋 Задания"),
                KeyboardButton(text="📮 Отчёт"),
            ],
            [
                KeyboardButton(text="📈 Прогресс"),
                KeyboardButton(text="❓ Помощь"),
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие",
    )
    return keyboard


def get_back_button():
    """Кнопка возврата в главное меню."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🏠 Главное меню")]
        ],
        resize_keyboard=True,
    )
    return keyboard


def get_tasks_keyboard(challenges: Sequence[tuple[str, str]]):
    """Inline-клавиатура со списком доступных заданий."""
    inline_keyboard = [
        [
            InlineKeyboardButton(
                text=title,
                callback_data=f"challenge_select:{challenge_id}",
            )
        ]
        for challenge_id, title in challenges
    ]
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


def get_challenge_actions_keyboard(challenge_id: str):
    """Inline-клавиатура с кнопками принятия или отказа от задания."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Принять задание ✅",
                    callback_data=f"challenge_accept:{challenge_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="Отказаться ❌",
                    callback_data=f"challenge_decline:{challenge_id}",
                )
            ],
        ]
    )


def get_report_challenges_keyboard(challenges: Iterable[tuple[str, str]]):
    """Inline-клавиатура с заданиями, по которым нужно отправить отчёт."""
    inline_keyboard = [
        [
            InlineKeyboardButton(
                text=title,
                callback_data=f"challenge_report:{challenge_id}",
            )
        ]
        for challenge_id, title in challenges
    ]
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


def get_report_confirmation_keyboard():
    """Inline-клавиатура для подтверждения или повторной отправки отчёта."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Подтвердить отчёт ✅",
                    callback_data="report_confirm",
                )
            ],
            [
                InlineKeyboardButton(
                    text="Редактировать отправленное ✏️",
                    callback_data="report_edit",
                )
            ],
        ]
    )
