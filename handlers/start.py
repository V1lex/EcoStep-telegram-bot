from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message, FSInputFile
from keyboards.all_keyboards import get_main_menu

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    """Обработка команды /start с картинкой и кнопками"""
    photo = FSInputFile("images/start_banner.jpg")  # относительный путь от корня проекта
    await message.answer_photo(
        photo=photo,
        caption="🌿 Бот пока что в разработке.\nСпасибо, что заглянул!\n\nВыберите действие из меню ниже:",
        reply_markup=get_main_menu()
    )
