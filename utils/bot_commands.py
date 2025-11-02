import logging

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import BotCommand, BotCommandScopeChat

from config.admins import ADMIN_IDS, has_admin_panel


async def setup_bot_commands(bot: Bot):
    """Настроить список команд для пользователя и админов."""
    common_commands = [
        BotCommand(command="start", description="Запустить бота"),
    ]
    await bot.set_my_commands(common_commands)

    if not ADMIN_IDS:
        return

    admin_commands = common_commands + [
        BotCommand(
            command="admin",
            description="Открыть админ-панель" if has_admin_panel() else "Админ-панель"
        )
    ]
    for admin_id in ADMIN_IDS:
        try:
            await bot.set_my_commands(
                commands=admin_commands,
                scope=BotCommandScopeChat(chat_id=admin_id)
            )
        except TelegramBadRequest as error:
            logging.warning("Не удалось назначить команды для администратора %s: %s", admin_id, error.message)
