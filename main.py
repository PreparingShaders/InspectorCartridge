#
# Этот блок только для рабочего ноута
import ssl
from ssl_off import unsafe_create_default_context
ssl.create_default_context = unsafe_create_default_context
# -------------


import asyncio
from db import save_transaction
from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message, CallbackQuery
from auth.auth import check_password
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

bot = AsyncTeleBot(os.environ["TELEGRAM_TESTBOT"])

# --- Глобальные состояния ---
USER_STATES = {}  # user_id -> словарь состояния

# --- Утилита для сброса состояния ---
def reset_state(user_id):
    USER_STATES[user_id] = {
        "step": None,
        "role": None,
        "warehouse": None,
        "operation": None,
        "model": None,
        "barcode": None,
        "comment": None,
    }
def reset_state_for_next_transaction(user_id):
    state = get_state(user_id)
    state["step"] = "awaiting_action"  # возвращаемся к выбору действия
    state["operation"] = None
    state["model"] = None
    state["barcode"] = None
    state["comment"] = None

# --- Проверка и создание состояния ---
def get_state(user_id):
    if user_id not in USER_STATES:
        reset_state(user_id)
    return USER_STATES[user_id]

# --- Старт и авторизация ---
@bot.message_handler(commands=["start"])
async def start(message: Message):
    user_id = message.from_user.id
    state = get_state(user_id)

    if state.get("role"):
        await bot.send_message(user_id, "Вы уже авторизованы.")
        await send_action_menu(user_id)
        return

    state["step"] = "awaiting_password"
    await bot.send_message(user_id, "Привет! Введите пароль для авторизации:")


@bot.message_handler(func=lambda m: True)
async def main_handler(message: Message):
    user_id = message.from_user.id
    state = get_state(user_id)
    text = message.text.strip()

    # --- Выйти ---
    if text == "🚪 Выйти":
        reset_state(user_id)
        await bot.send_message(user_id, "Вы вышли из аккаунта. Используйте /start для новой авторизации.")
        return

    # --- Шаги ---
    if state["step"] == "awaiting_password":
        role = check_password(user_id, text)
        if role:
            state["role"] = role
            state["step"] = "awaiting_warehouse"
            await bot.send_message(user_id, f"Вы авторизованы как {role}. Выберите склад:", reply_markup=get_warehouse_menu())
        else:
            await bot.send_message(user_id, "Неверный пароль. Попробуйте снова.")
        return

    if state["step"] == "awaiting_warehouse":
        warehouses_map = {
            "🏬 Невская": "Невская",
            "🏬 Новороссийская": "Новороссийская"
        }

        if text in warehouses_map:
            state["warehouse"] = warehouses_map[text]  # сохраняем без эмодзи
            state["step"] = "awaiting_action"
            await send_action_menu(user_id)
        else:
            await bot.send_message(user_id, "Выберите склад через кнопки.")
        return

    if state["step"] == "awaiting_action":
        if text == "📥 Приход" and state["role"] == "admin":
            state["operation"] = "приход"
            await bot.send_message(user_id, "Выберите модель картриджа:", reply_markup=get_cartridge_inline_keyboard())
            state["step"] = "awaiting_model"
        elif text == "📤 Расход":
            state["operation"] = "расход"
            await bot.send_message(user_id, "Выберите модель картриджа:", reply_markup=get_cartridge_inline_keyboard())
            state["step"] = "awaiting_model"
        elif text == "📊 Складской запас" and state["role"] == "admin":
            await handle_admin_stock(bot, user_id)
        else:
            await bot.send_message(user_id, "Выберите действие через кнопки.")
        return

    if state["step"] == "awaiting_barcode":
        # Ввод штрих-кода
        barcode = text if text.lower() not in ["нет кода", "пропустить"] else "отсутствует"
        state["barcode"] = barcode
        state["step"] = "confirm_barcode"
        state["step"] = "awaiting_comment"  # Новый шаг
        await bot.send_message(user_id, "Введите комментарий (например, имя пользователя, отдел, причина и т.п.):")
        return

    if state["step"] == "awaiting_comment":
        state["comment"] = text
        state["step"] = "confirm_barcode"
        await bot.send_message(
            user_id,
            f"Мы {'принимаем' if state['operation'] == 'приход' else 'списываем'} картридж {state['model']} "
            f"на склад {state['warehouse']} с серийным номером {state['barcode']}.\n"
            f"Комментарий: {state['comment']}\n"
            f"Верно?",
            reply_markup=get_confirm_menu()
        )
        return

    if state["step"] == "confirm_barcode":
        if text == "Верно":
            username = message.from_user.username or message.from_user.first_name
            try:
                save_transaction(state, username)
                await bot.send_message(user_id, "✅ Операция успешно сохранена в базе данных.")
                reset_state_for_next_transaction(user_id)
                await send_action_menu(user_id)
            except Exception as e:
                await bot.send_message(user_id, f"❌ Ошибка при сохранении: {e}")
                reset_state_for_next_transaction(user_id)
                await send_action_menu(user_id)

        elif text == "Я ошибся":
            state["step"] = "awaiting_barcode"
            state["barcode"] = None
            await bot.send_message(
                user_id,
                "Введите штрих-код заново или выберите картридж:",
                reply_markup=get_barcode_menu()
            )
        return

# --- Inline callback для выбора модели ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("cartridge:"))
async def handle_model_callback(call: CallbackQuery):
    user_id = call.from_user.id
    state = get_state(user_id)
    model = call.data.split(":", 1)[1]

    state["model"] = model
    state["step"] = "awaiting_barcode"

    await bot.answer_callback_query(call.id)
    await bot.send_message(user_id, f"Введите штрих-код для модели {model}.\nЕсли кода нет, нажмите кнопку 'Нет кода':",
                                   reply_markup=get_barcode_menu())


# --- Функция для показа меню действий ---
async def send_action_menu(user_id):
    state = get_state(user_id)
    if state["role"] == "admin":
        await bot.send_message(user_id, f"Выберите действие:", reply_markup=get_admin_menu())
    else:
        await bot.send_message(user_id, f"Выберите действие:", reply_markup=get_user_menu())

# --- Точка входа ---
async def main():
    print("Бот запущен")
    await bot.polling()

if __name__ == "__main__":
    asyncio.run(main())
