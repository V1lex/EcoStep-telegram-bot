from urllib.parse import urlparse

from aiogram.types import Message
from config.admins import ADMIN_WEBAPP_URL, has_admin_panel, is_admin
from keyboards.all_keyboards import get_admin_panel_keyboard


async def send_admin_panel_prompt(message: Message, user_id: int):
    """Отправить кнопку открытия админской mini app, если пользователь — админ."""
    if not is_admin(user_id):
        return
    if not has_admin_panel():
        return
    parsed = urlparse(ADMIN_WEBAPP_URL)
    if parsed.scheme.lower() != "https":
        return

    await message.answer(
        "🛠 <b>Админ-панель</b>\nОткрой mini app, чтобы управлять ботом.",
        reply_markup=get_admin_panel_keyboard(ADMIN_WEBAPP_URL),
    )
