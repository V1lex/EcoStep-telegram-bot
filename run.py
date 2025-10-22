import asyncio
from create_bot import dp, bot
from handlers import start

async def main():
    dp.include_router(start.router)

    print("✅ Bot is running...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
