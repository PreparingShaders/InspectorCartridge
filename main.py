# Этот блок только для рабочего ноута
import ssl
from ssl_off import unsafe_create_default_context
ssl.create_default_context = unsafe_create_default_context
# -------------

import asyncio
from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message
from auth.auth import check_password, get_role
from ui.menu import get_admin_menu, get_user_menu, get_warehouse_menu
from actions import handle_user_expense, handle_admin_income, handle_admin_stock
import os
from db import init_db, seed_data

init_db()  # при запуске
seed_data()

# Состояния пользователей
USER_STATES = {}  # user_id: {'step': str, 'warehouse': str | None, 'model': str | None}
USER_STATE = {}  # user_id: 'awaiting_password' | None
AUTHORIZED_USERS = {}  # user_id: role

bot = AsyncTeleBot(os.environ["TELEGRAM_TESTBOT"])


# === Стартовая команда / авторизация ===
@bot.message_handler(commands=["start"])
async def start(message: Message):
    user_id = message.from_user.id
    role = AUTHORIZED_USERS.get(user_id)

    if role:
        await send_welcome_with_menu(user_id, role)
        return

    await bot.send_message(user_id, "Привет! Введите пароль для авторизации:")
    USER_STATE[user_id] = "awaiting_password"


# === Показываем меню выбора склада ===
async def send_welcome_with_menu(user_id: int, role: str):
    USER_STATES[user_id] = {'step': 'awaiting_warehouse', 'warehouse': None, 'model': None}
    text = f"Вы успешно авторизованы как {role}! Выберите склад:"
    await bot.send_message(user_id, text, reply_markup=get_warehouse_menu())


# === Обработка выбора склада ===
@bot.message_handler(func=lambda message: message.text in ["🏬 Невская", "🏬 Новороссийская"])
async def handle_warehouse_selection(message: Message):
    user_id = message.from_user.id
    state = USER_STATES.get(user_id)

    if not state or state.get('step') != 'awaiting_warehouse':
        return

    # Сохраняем склад
    USER_STATES[user_id]['warehouse'] = message.text
    USER_STATES[user_id]['step'] = None

    role = AUTHORIZED_USERS.get(user_id)
    if not role:
        await bot.send_message(user_id, "Ошибка: вы не авторизованы.")
        return

    await bot.send_message(
        user_id,
        f"Вы выбрали {message.text}. Выберите действие:",
        reply_markup=get_admin_menu() if role == "admin" else get_user_menu()
    )


# === ОБЩИЙ ХЕНДЛЕР ВСЕХ ОСТАЛЬНЫХ СООБЩЕНИЙ (последним!) ===
@bot.message_handler(func=lambda m: True)
async def handle_messages(message: Message):
    user_id = message.from_user.id
    role = AUTHORIZED_USERS.get(user_id)

    # --- Ждём пароль ---
    if USER_STATE.get(user_id) == "awaiting_password":
        password = message.text.strip()
        role = check_password(user_id, password)
        if role:
            AUTHORIZED_USERS[user_id] = role
            USER_STATE[user_id] = None
            await send_welcome_with_menu(user_id, role)
        else:
            await bot.send_message(user_id, "Неверный пароль. Попробуйте снова.")
        return

    # --- Выйти ---
    if message.text == "🚪 Выйти":
        AUTHORIZED_USERS.pop(user_id, None)
        USER_STATE[user_id] = None
        USER_STATES.pop(user_id, None)
        await bot.send_message(user_id, "Вы вышли из аккаунта. Используйте /start для новой авторизации.")
        return

    # --- Логика админа ---
    if role == "admin":
        if message.text == "📥 Приход":
            await handle_admin_income(bot, user_id)
        elif message.text == "📊 Складской запас":
            await handle_admin_stock(bot, user_id)
        elif message.text == "📤 Расход":
            await handle_user_expense(bot, user_id)
        return

    # --- Логика пользователя ---
    if role == "user":
        if message.text == "📤 Расход":
            await handle_user_expense(bot, user_id)
        elif message.text == "❓ Помощь":
            await bot.send_message(user_id, "Здесь будет справка по использованию бота")
        return

    # --- Неавторизован ---
    await bot.send_message(user_id, "Сначала введите пароль через /start")


# === Точка входа ===
async def main():
    print('Бот запущен')
    await bot.polling()


if __name__ == "__main__":
    asyncio.run(main())
