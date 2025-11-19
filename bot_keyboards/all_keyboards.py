from collections.abc import Iterable, Sequence

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
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
            [
                KeyboardButton(
                    text="🗺 Карта экологии",
                    web_app=WebAppInfo(url="https://recyclemap.ru/"),
                ),
                KeyboardButton(text="🏅 Рейтинг друзей"),
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


def get_admin_panel_keyboard(url: str):
    """Inline-клавиатура для открытия админской mini app."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🛠 Открыть админ-панель",
                    web_app=WebAppInfo(url=url),
                )
            ]
        ]
    )


def get_friend_actions_keyboard(has_friends: bool):
    """Кнопки действий в разделе друзей."""
    inline_keyboard = [
        [InlineKeyboardButton(text="➕ Добавить друга", callback_data="friends:add")],
    ]
    if has_friends:
        inline_keyboard.append(
            [InlineKeyboardButton(text="➖ Удалить друга", callback_data="friends:remove")]
        )
    inline_keyboard.append(
        [InlineKeyboardButton(text="🔁 Обновить рейтинг", callback_data="friends:refresh")]
    )
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


def get_friend_confirmation_keyboard(friend_id: int):
    """Клавиатура подтверждения добавления друга."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Добавить",
                    callback_data=f"friends:confirm_add:{friend_id}",
                )
            ],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="friends:cancel")],
        ]
    )


def get_friend_remove_keyboard(items: Sequence[tuple[int, str]]):
    """Клавиатура выбора друга для удаления."""
    inline_keyboard = [
        [
            InlineKeyboardButton(
                text=label,
                callback_data=f"friends:remove_select:{friend_id}",
            )
        ]
        for friend_id, label in items
    ]
    inline_keyboard.append([InlineKeyboardButton(text="❌ Отмена", callback_data="friends:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


def get_friend_cancel_keyboard():
    """Клавиатура с кнопкой отмены."""
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data="friends:cancel")]]
    )


def get_friend_request_keyboard(request_id: int):
    """Клавиатура для подтверждения заявки в друзья."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Принять",
                    callback_data=f"friends:req_accept:{request_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🚫 Отклонить",
                    callback_data=f"friends:req_decline:{request_id}",
                )
            ],
        ]
    )
