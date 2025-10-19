import asyncio
from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message, CallbackQuery
from auth.auth import check_password, get_role
from ui.menu import (
    get_admin_menu,
    get_user_menu,
    get_warehouse_menu,
    get_cartridge_inline_keyboard,
    get_barcode_menu,
    get_confirm_menu
)

from actions import handle_user_expense, handle_admin_income, handle_admin_stock
import os
from db import init_db

# Инициализация базы
init_db()

# --- Состояния пользователей ---
USER_STATES = {}  # user_id: {'step': str, 'warehouse': str | None, 'model': str | None, 'barcode': str | None}
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
    USER_STATES[user_id] = {'step': 'awaiting_password', 'warehouse': None, 'model': None, 'barcode': None}


# === Показываем меню выбора склада ===
async def send_welcome_with_menu(user_id: int, role: str):
    USER_STATES[user_id] = {'step': 'awaiting_warehouse', 'warehouse': None, 'model': None, 'barcode': None}
    text = f"Вы успешно авторизованы как {role}! Выберите склад:"
    await bot.send_message(user_id, text, reply_markup=get_warehouse_menu())


# === Обработка выбора склада ===
@bot.message_handler(func=lambda message: message.text in ["🏬 Невская", "🏬 Новороссийская"])
async def handle_warehouse_selection(message: Message):
    user_id = message.from_user.id
    state = USER_STATES.get(user_id)

    if not state or state.get('step') != 'awaiting_warehouse':
        return

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


# === Callback для выбора картриджа ===
@bot.callback_query_handler(func=lambda call: call.data.startswith("cartridge:"))
async def handle_cartridge_callback(call: CallbackQuery):
    user_id = call.from_user.id
    model = call.data.split(":", 1)[1]

    # сохраняем выбор модели
    USER_STATES[user_id] = {
        "step": "awaiting_barcode",
        "model": model,
        "warehouse": USER_STATES.get(user_id, {}).get("warehouse"),
        "barcode": None
    }

    await bot.answer_callback_query(call.id)
    await bot.send_message(
        user_id,
        f"Введите штрих-код для модели {model}.\nЕсли кода нет, нажмите кнопку 'Нет кода':",
        reply_markup=get_barcode_menu()
    )


# === Хендлер для ввода штрих-кода ===
@bot.message_handler(func=lambda message: USER_STATES.get(message.from_user.id, {}).get('step') == 'awaiting_barcode')
async def handle_barcode_input(message: Message):
    user_id = message.from_user.id
    state = USER_STATES.get(user_id)
    if not state:
        return

    role = AUTHORIZED_USERS.get(user_id)
    text = message.text.strip().lower()

    if text == "нет кода" or text == "пропустить":
        barcode = "отсутствует"
    else:
        barcode = message.text.strip()

    USER_STATES[user_id]['barcode'] = barcode
    USER_STATES[user_id]['step'] = 'confirm_barcode'

    # Просим подтвердить
    await bot.send_message(
        user_id,
        f"Мы списываем картридж {state['model']} со склада {state['warehouse']} с серийным номером {barcode}, верно?",
        reply_markup=get_confirm_menu()
    )


# === Общий хендлер всех остальных сообщений ===
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

    # --- Подтверждение списания ---
    if state.get('step') == 'confirm_barcode':
        if message.text == "Верно":
            # Здесь вызываем функцию списания
            await handle_user_expense(bot, user_id, state['model'], state['barcode'], state['warehouse'])
            await bot.send_message(user_id, "Картридж списан!", reply_markup=get_admin_menu() if role == "admin" else get_user_menu())
        elif message.text == "Я ошибся":
            await bot.send_message(user_id, "Операция отменена. Введите штрих-код заново или выберите картридж.", reply_markup=None)
        USER_STATES[user_id]['step'] = None
        USER_STATES[user_id]['barcode'] = None
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
