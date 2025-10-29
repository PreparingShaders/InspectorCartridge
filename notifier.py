# notifier.py
import os
from telebot.async_telebot import AsyncTeleBot
from dotenv import load_dotenv
from actions import handle_admin_stock  # твоя async функция

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT")
GROUP_CHAT_ID = int(os.getenv("GROUP_CHAT_ID"))
THREAD_ID = int(os.getenv("THREAD_ID"))

bot = AsyncTeleBot(BOT_TOKEN)


async def notify_admin_stock():
    await bot.send_message(GROUP_CHAT_ID, "👋 Приветствие", message_thread_id=THREAD_ID, parse_mode="HTML")
    await handle_admin_stock(bot, GROUP_CHAT_ID, THREAD_ID)
