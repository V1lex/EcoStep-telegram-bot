import asyncio
import logging
from aiogram import Bot
from aiogram.types import Message
from create_bot import dp, bot
from handlers import start, analytics
from database import init_db, register_user

# Подключаем обработчики
dp.include_router(start.router)
dp.include_router(analytics.router)

# Middleware для автоматической регистрации
async def register_middleware(handler, event, data):
    """Middleware для регистрации пользователей"""
    if isinstance(event, Message) and event.from_user:
        user_id = event.from_user.id
        username = event.from_user.username or "неизвестно"
        first_name = event.from_user.first_name or "Пользователь"
        register_user(user_id, username, first_name)
    
    return await handler(event, data)

async def main():
    # Инициализация базы данных
    init_db()
    
    # Подключаем middleware для регистрации
    dp.message.middleware(register_middleware)
    
    logging.basicConfig(level=logging.INFO)
    print("✅ Bot is running...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
