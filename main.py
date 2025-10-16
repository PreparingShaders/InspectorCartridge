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
        await bot.send_message(user_id, f"Вы уже авторизованы как {role}")
        await bot.send_message(user_id, "Меню:", reply_markup=get_admin_menu() if role == "admin" else get_user_menu())
        return

    await bot.send_message(user_id, "Привет! Введите пароль для авторизации:")
    USER_STATE[user_id] = "awaiting_password"

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
            await bot.send_message(user_id, f"Вы успешно авторизованы как {role}!")
            await bot.send_message(user_id, "Меню:", reply_markup=get_admin_menu() if role == "admin" else get_user_menu())
        else:
            await bot.send_message(user_id, "Неверный пароль, попробуйте снова:")
        return

    # --- Кнопка выхода ---
    if message.text == "🚪 Выйти":
        if user_id in AUTHORIZED_USERS:
            del AUTHORIZED_USERS[user_id]
        USER_STATE[user_id] = None
        await bot.send_message(user_id, "Вы вышли из аккаунта. Используйте /start для новой авторизации.")
        return

    # --- Логика пользователя ---
    if role == "user":
        if message.text == "🛒 Посмотреть товары":
            await bot.send_message(user_id, "Функция просмотра товаров пока не реализована")
        elif message.text == "📦 Проверить наличие":
            await bot.send_message(user_id, "Функция проверки наличия пока не реализована")
        elif message.text == "❓ Помощь":
            await bot.send_message(user_id, "Здесь будет справка по использованию бота")
        else:
            await bot.send_message(user_id, "Выберите действие с помощью кнопок меню")
        return

    # --- Логика админа ---
    if role == "admin":
        if message.text == "📥 Принять на склад":
            await bot.send_message(user_id, "Функция принятия на склад пока не реализована")
        elif message.text == "📊 Запросить остаток":
            await bot.send_message(user_id, "Функция запроса остатка пока не реализована")
        elif message.text == "📤 Списать со склада":
            await bot.send_message(user_id, "Функция списания со склада пока не реализована")
        else:
            await bot.send_message(user_id, "Выберите действие с помощью кнопок меню")
        return

    # --- Если не авторизован ---
    await bot.send_message(user_id, "Сначала введите пароль через /start")

async def main():
    print('Бот запущен')
    await bot.polling()

if __name__ == "__main__":
    asyncio.run(main())
