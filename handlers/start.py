# handlers/start.py
from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile

router = Router()

@router.message(CommandStart())
async def cmd_start(message: "types.Message"):
    photo = FSInputFile("images/start_banner.jpg")  # относительный путь от корня проекта
    await message.answer_photo(
        photo=photo,
        caption="🌿 Бот пока что в разработке.\nСпасибо, что заглянул!"
    )
