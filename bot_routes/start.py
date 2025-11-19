from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile, Message

from bot_keyboards.all_keyboards import get_main_menu
from support_tools.admin_panel import send_admin_panel_prompt

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    """Обработка команды /start с приветствием"""
    user_id = message.from_user.id
    first_name = message.from_user.first_name or "Пользователь"
    
    # Формируем текст приветствия
    caption_text = (
        f"🌿 Привет, {first_name}!\n\n"
        "Добро пожаловать в EcoStep — бот для формирования экологических привычек.\n\n"
        "Выберите действие из меню ниже:"
    )
    
    # Отправка фото с текстом и кнопками
    photo = FSInputFile("assets/start_banner.jpg")
    await message.answer_photo(
        photo=photo,
        caption=caption_text,
        reply_markup=get_main_menu()
    )
    await send_admin_panel_prompt(message, user_id)
