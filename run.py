import asyncio
from create_bot import dp, bot
from handlers import start, analytics  # ← добавил analytics

async def main():
    dp.include_router(start.router)
    dp.include_router(analytics.router)  # ← добавил эту строчку

    print("✅ Bot is running...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
