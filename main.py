#Этот блок только для рабочего ноута,
# отключаем ssl проверку импортируем функцию из файлика ssl_off
import  ssl
from ssl_off import unsafe_create_default_context
ssl.create_default_context = unsafe_create_default_context
#--------------

import asyncio
from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message
from auth.auth import check_password, get_role
from ui.menu import get_admin_menu, get_user_menu
import os

bot = AsyncTeleBot(os.environ["TELEGRAM_TESTBOT"])

USER_STATE = {}  # user_id: 'awaiting_password' | None
AUTHORIZED_USERS = {}  # user_id: role

@bot.message_handler(commands=["start"])
async def start(message: Message):
    user_id = message.from_user.id
    role = AUTHORIZED_USERS.get(user_id)  # проверяем текущую авторизацию

    if role:
        await send_welcome_with_menu(user_id, role)
        return

    await bot.send_message(user_id, "Привет! Введите пароль для авторизации:")
    USER_STATE[user_id] = "awaiting_password"

async def send_welcome_with_menu(user_id: int, role: str):
    menu = get_admin_menu() if role == "admin" else get_user_menu()
    text = f"Вы успешно авторизованы как {role}! Выберите действие:"
    await bot.send_message(user_id, text, reply_markup=menu)


@bot.message_handler(func=lambda m: True)
async def handle_messages(message: Message):
    user_id = message.from_user.id
    role = AUTHORIZED_USERS.get(user_id)  # берём роль из текущих авторизованных

    # --- Ждем пароль ---
    if USER_STATE.get(user_id) == "awaiting_password":
        password = message.text.strip()
        role = check_password(user_id, password)
        if role:
            AUTHORIZED_USERS[user_id] = role
            USER_STATE[user_id] = None
            await send_welcome_with_menu(user_id, role)

    # --- Кнопка выхода ---
    if message.text == "🚪 Выйти":
        if user_id in AUTHORIZED_USERS:
            del AUTHORIZED_USERS[user_id]
        USER_STATE[user_id] = None
        await bot.send_message(user_id, "Вы вышли из аккаунта. Используйте /start для новой авторизации.")
        return

    # --- Логика пользователя ---
    if role == "user":
        if message.text == "📤 Расход":
            await bot.send_message(user_id, "Функция списания картриджей пока не реализована")
        elif message.text == "❓ Помощь":
            await bot.send_message(user_id, "Здесь будет справка по использованию бота")
        return

    # --- Логика админа ---
    if role == "admin":
        if message.text == "📥 Приход":
            await bot.send_message(user_id, "Функция принятия на склад пока не реализована")
        elif message.text == "📊 Складской запас":
            await bot.send_message(user_id, "Функция запроса остатка пока не реализована")
        elif message.text == "📤 Расход":
            await bot.send_message(user_id, "Функция списания со склада пока не реализована")
        return

    # --- Если не авторизован ---
    await bot.send_message(user_id, "Сначала введите пароль через /start")

async def main():
    print('Бот запущен')
    await bot.polling()

if __name__ == "__main__":
    asyncio.run(main())
