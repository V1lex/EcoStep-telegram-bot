import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set in .env")

bot = Bot(
    token=BOT_TOKEN, 
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()