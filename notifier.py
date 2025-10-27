# notifier.py
import os
from telebot import TeleBot
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_TESTBOT")
GROUP_CHAT_ID = int(os.getenv("GROUP_CHAT_ID"))  # здесь берем имя переменной, а не число
THREAD_ID = int(os.getenv("THREAD_ID"))

bot = TeleBot(BOT_TOKEN)

def send_catalog_message(text: str):
    """Отправляет сообщение в конкретный каталог (тему) внутри группы."""
    try:
        bot.send_message(GROUP_CHAT_ID, text, message_thread_id=THREAD_ID)
        print(f"[INFO] Уведомление отправлено в каталог: {text}")
    except Exception as e:
        print(f"[ERROR] Не удалось отправить сообщение в каталог: {e}")
