import asyncio
from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message
from auth.auth import check_password, get_role
from ui.menu import get_admin_menu, get_user_menu, get_warehouse_menu, get_cartridge_type_keyboard
from actions import handle_user_expense, handle_admin_income, handle_admin_stock
import os
from db import init_db, seed_data

# Инициализация базы
init_db()
seed_data()

# --- Состояния пользователей ---
USER_STATES = {}  # user_id: {'step': str, 'warehouse': str | None, 'model': str | None}
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
    USER_STATES[user_id] = {'step': 'awaiting_password', 'warehouse': None, 'model': None}


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
    USER_STATES[user_id]['model'] = message.text  # для inline-кнопок
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


# === Хендлер для Приход/Расход ===
@bot.message_handler(func=lambda m: m.text in ["📥 Приход", "📤 Расход"])
async def handle_flow(msg):
    user_id = msg.from_user.id
    user_state = USER_STATES.get(user_id)

    if not user_state or not user_state.get("model"):
        await bot.send_message(msg.chat.id, "Сначала выберите склад!", reply_markup=get_warehouse_menu())
        return

    model = user_state["model"]
    action = "income" if msg.text == "📥 Приход" else "outcome"
    kb = get_cartridge_type_keyboard(action, model)
    if not kb:
        await bot.send_message(msg.chat.id, "Картриджи для этого склада не найдены.", reply_markup=get_admin_menu())
        return

    await bot.send_message(msg.chat.id, "Выберите тип картриджа:", reply_markup=kb)


# === ОБЩИЙ ХЕНДЛЕР ВСЕХ ОСТАЛЬНЫХ СООБЩЕНИЙ ===
@bot.message_handler(func=lambda m: True)
async def handle_messages(message: Message):
    user_id = message.from_user.id
    state = USER_STATES.get(user_id, {})
    role = AUTHORIZED_USERS.get(user_id)

    # --- Ждём пароль ---
    if state.get('step') == "awaiting_password":
        password = message.text.strip()
        role = check_password(user_id, password)
        if role:
            AUTHORIZED_USERS[user_id] = role
            await send_welcome_with_menu(user_id, role)
        else:
            await bot.send_message(user_id, "Неверный пароль. Попробуйте снова.")
        return

    # --- Выйти ---
    if message.text == "🚪 Выйти":
        AUTHORIZED_USERS.pop(user_id, None)
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
        elif message.text == "❓ Помощь":
            await bot.send_message(user_id, """
🧾 Справка по использованию бота
Бот предназначен для учёта картриджей на складе.
Он позволяет:
📦 Принимать и выдавать картриджи;
📊 Вести учёт текущего потребления и остатка на складе;
🔢 Сканировать или вводить штрих-коды (баркоды);
💾 Сохранять данные о картриджах в базе.

Используйте кнопки меню для выполнения операций и получения актуальной информации по складу.
            """)
        return

    # --- Логика пользователя ---
    if role == "user":
        if message.text == "📤 Расход":
            await handle_user_expense(bot, user_id)
        elif message.text == "❓ Помощь":
            await bot.send_message(user_id, """
🧾 Справка по использованию бота
Бот предназначен для учёта картриджей на складе.
Он позволяет:
📦 Принимать и выдавать картриджи;
📊 Вести учёт текущего потребления и остатка на складе;
🔢 Сканировать или вводить штрих-коды (баркоды);
💾 Сохранять данные о картриджах в базе.

Используйте кнопки меню для выполнения операций и получения актуальной информации по складу.
            """)
        return

    # --- Неавторизован ---
    await bot.send_message(user_id, "Сначала введите пароль через /start")


# === Точка входа ===
async def main():
    print('Бот запущен')
    await bot.polling()


if __name__ == "__main__":
    asyncio.run(main())
