# Этот блок только для рабочего ноута
# 9
# -------------
# -1001758030666 GROUP_CHAT_ID
# 2 это ID личного чата с ботом

import os
os.environ["DYLD_LIBRARY_PATH"] = "/opt/homebrew/lib:" + os.environ.get("DYLD_LIBRARY_PATH", "")


import asyncio
from handlers.barcode_scan import init_barcode_handler
from db import save_transaction, export_database_to_excel, DB_NAME
from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message, CallbackQuery
from auth.auth import check_password
from ui.menu import (
    get_admin_menu,
    get_user_menu,
    get_warehouse_menu,
    get_cartridge_inline_keyboard,
    get_barcode_menu,
    get_confirm_menu,
    get_after_operation_menu,
    get_comment_menu,
    get_logs_keyboard

)
from actions import handle_user_expense, handle_admin_income, handle_admin_stock, handle_admin_logs, notify_low_stock
import os
from db import init_db
import notifier
from datetime import datetime, timedelta
# Инициализация базы
init_db()

GROUP_CHAT_ID = int(os.getenv("GROUP_CHAT_ID"))
THREAD_ID = int(os.getenv("THREAD_ID"))
bot = AsyncTeleBot(os.environ["TELEGRAM_BOT"])

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


# --- Инициализация обработчика штрих-кодов ---
init_barcode_handler(bot, get_state)

# --- Команда сброса ---
@bot.message_handler(commands=["reset"])
async def reset_command(message: Message):
    user_id = message.from_user.id
    reset_state(user_id)
    await bot.send_message(user_id, "Сессия сброшена. Введите /start для авторизации.")

# --- обработчик ---
@bot.callback_query_handler(func=lambda call: call.data == "export_excel")
async def export_excel_callback(call):
    excel_path = None
    try:
        excel_path = export_database_to_excel(DB_NAME)  # твоя база
        with open(excel_path, "rb") as f:
            await bot.send_document(call.message.chat.id, f, caption="📊 Полная выгрузка базы данных")
    except Exception as e:
        await bot.send_message(call.message.chat.id, f"⚠ Ошибка при выгрузке: {e}")
    finally:
        if excel_path and os.path.exists(excel_path):
            os.remove(excel_path)


@bot.callback_query_handler(func=lambda call: call.data.startswith("logs_page:"))
async def handle_logs_page_callback(call: CallbackQuery):
    """
    Обработчик кнопок пагинации логов.
    Формат callback_data: logs_page:{page}:{from_ts}:{to_ts}
    """
    from actions import handle_admin_logs  # чтобы избежать циклического импорта

    user_id = call.from_user.id
    state = USER_STATES.get(user_id, {})

    try:
        # Разбираем данные: logs_page:page:from_ts:to_ts
        parts = call.data.split(":")
        if len(parts) != 4:
            raise ValueError(f"Неверный формат callback_data: {call.data}")

        _, page_str, from_ts_str, to_ts_str = parts
        page = int(page_str)
        date_from = datetime.fromtimestamp(int(from_ts_str))
        date_to = datetime.fromtimestamp(int(to_ts_str))

        await handle_admin_logs(bot, user_id, state, date_from=date_from, date_to=date_to, page=page)
        await bot.answer_callback_query(call.id)

    except Exception as e:
        import traceback
        traceback.print_exc()
        await bot.answer_callback_query(call.id, f"⚠ Ошибка при переключении страницы: {e}")


# --- Старт и авторизация ---
@bot.message_handler(commands=["start"])
async def start(message: Message):
    user_id = message.from_user.id
    state = get_state(user_id)

    if state.get("role"):
        state["step"] = "awaiting_warehouse"
        state["warehouse"] = None  # сбрасываем склад
        await bot.send_message(user_id, "Вы уже авторизованы. Пожалуйста, выберите склад:",
                               reply_markup=get_warehouse_menu())
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

    # --- Назад ---
    if text == "◀️ Назад":
        step = state["step"]

        if step == "awaiting_action":
            state["step"] = "awaiting_warehouse"
            await bot.send_message(user_id, "Выберите склад:", reply_markup=get_warehouse_menu())
            return

        elif step == "awaiting_warehouse":
            state["step"] = "awaiting_password"
            state["warehouse"] = None
            await bot.send_message(user_id, "Вы вернулись на шаг авторизации. Введите пароль:")
            return

        elif step == "awaiting_model":
            state["step"] = "awaiting_action"
            await send_action_menu(user_id)
            return

        elif step == "awaiting_barcode":
            state["step"] = "awaiting_model"
            await bot.send_message(user_id, "Выберите модель картриджа:", reply_markup=get_cartridge_inline_keyboard())
            return

        elif step == "awaiting_comment":
            state["step"] = "awaiting_barcode"
            await bot.send_message(user_id, "Введите штрих-код заново:", reply_markup=get_barcode_menu())
            return

        elif step == "awaiting_quantity":
            state["step"] = "awaiting_comment"
            await bot.send_message(user_id, "Введите комментарий заново:")
            return

        elif step == "confirm_barcode":
            state["step"] = "awaiting_comment"
            await bot.send_message(user_id, "Введите комментарий заново:")
            return

        elif step == "awaiting_logs_period":
            state["step"] = "awaiting_action"
            await send_action_menu(user_id)
            return

        await bot.send_message(user_id, "Неизвестный шаг для возврата назад. Нажмите /start или /reset.")
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
            state["warehouse"] = warehouses_map[text]
            state["step"] = "awaiting_action"
            await send_action_menu(user_id)
            return

        elif text == "📊 Складской запас":
            await handle_admin_stock(bot, user_id)
            return

        else:
            await bot.send_message(user_id, """ℹ️ <b>Справка по боту</b>

            <b>1.</b> Отправьте команду <code>/start</code>
            <b>2.</b> Введите пароль для авторизации
            <b>3.</b> Выберите склад: 🏬 Невская или 🏬 Новороссийская

            <b>Доступные действия:</b>
            📥 <b>Приход</b> — добавить картриджи на склад  
            📤 <b>Расход</b> — списать картриджи с комментарием  
            📊 <b>Складской запас</b> — посмотреть остатки по моделям  
            📜 <b>История операций</b> — логи движений картриджей

            <b>Навигация:</b>
            ◀️ <b>Назад</b> — вернуться на предыдущий шаг  
            🔄 <b>Сброс</b> Для сброса, если что-то пошло не так. <code>/reset</code>
            🚪 <b>Выйти</b> — завершить сессию и выйти

            По всем вопросам обращайтесь к @Alexy_Polly.
            """, parse_mode="HTML")

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
        elif text == "📜 История операций" and state["role"] == "admin":
            kb = get_logs_keyboard()
            await bot.send_message(message.chat.id, "📊 Выберите период для просмотра логов:", reply_markup=kb)
            return

        else:
            await bot.send_message(user_id, "Выберите действие через кнопки.")
        return

    elif state["step"] in ["awaiting_logs_from", "awaiting_logs_to"]:
        await handle_admin_logs(bot, user_id, state, text)
        return

    # Ввод штрих-кода
    if state["step"] == "awaiting_barcode":
        if text.isdigit() and len(text) == 13:
            barcode = text
        elif text.lower() in ["нет кода"]:
            barcode =  "отсутствует"
        else:
            await bot.send_message(user_id,"Ошибка🚨\n🆔Штрих-код должен содержать ровно 13 цифр.\n\nЕсли нет кода нажмите >> 'Нет кода'.")
            return  # Ждём повторного ввода

        state["barcode"] = barcode
        state["step"] = "awaiting_comment"  # Новый шаг
        await bot.send_message(user_id, "💬 Введите комментарий (например, имя пользователя, отдел, желательно имя принтера с наклейки):", reply_markup=get_comment_menu())
        return

    if state["step"] == "awaiting_comment":
        state["comment"] = text
        state["step"] = "awaiting_quantity"
        await bot.send_message(
            user_id,
            "📦 Введите количество картриджей с данным штрих-кодом (например: 5)\n Если код другой операцию произвести через Расход или Приход"
        )
        return

    if state["step"] == "awaiting_quantity":
        if not text.isdigit() or int(text) <= 0 or int(text) > 20:
            await bot.send_message(user_id, "❌ Введите положительное число в диапозоне от 0 до 20 (например: 3).")
            return

        state["quantity"] = int(text)
        state["step"] = "confirm_barcode"

        await bot.send_message(
            user_id,
            f"❗{'Принимаем' if state['operation'] == 'приход' else 'Списываем'}:\n\n"
            f"🖨 Картридж: {state['model']}\n"
            f"🏬 Склад: {state['warehouse']}\n"
            f"🆔 Штрих-код: {state['barcode']}\n"
            f"💬 Комментарий: {state['comment']}\n"
            f"📦 Количество: {state['quantity']}\n\n"
            f"Верно?⁉️ Если да, то жми кнопку '✅ Верно'!",
            reply_markup=get_confirm_menu()
        )
        return

    if state["step"] == "confirm_barcode":
        if text == "✅ Верно":
            username = message.from_user.username or message.from_user.first_name
            try:
                warehouse_id, cartridge_type_id = save_transaction(state, username)
                await bot.send_message(user_id, "✅ Операция успешно сохранена в базе данных.")

                # --- Проверка остатков после расхода ---
                if state["operation"] == "расход":
                    await notify_low_stock(bot, GROUP_CHAT_ID, warehouse_id, cartridge_type_id, THREAD_ID)

                # Переходим к шагу повторения
                state["step"] = "after_operation"
                await bot.send_message(user_id, "Что делать дальше?", reply_markup=get_after_operation_menu())

            except Exception as e:
                await bot.send_message(user_id, f"❌ Ошибка при сохранении: {e}")
                reset_state_for_next_transaction(user_id)
                await send_action_menu(user_id)
            return

    if state["step"] == "after_operation":
        if text == "↩ Повторить":
            # Сбрасываем только штрих-код и комментарий
            state["barcode"] = None
            state["comment"] = None
            state["step"] = "awaiting_barcode"

            await bot.send_message(
                user_id,
                f"Введите 🆔 штрих-код для модели {state['model']} 🖨:",
                reply_markup=get_barcode_menu()
            )
            return

        elif text == "📋 Меню":
            reset_state_for_next_transaction(user_id)
            await send_action_menu(user_id)
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
    await bot.send_message(user_id, f"Введите 🆔 штрих-код для модели {model} 🖨 .\n\n❗Если кода нет, нажмите кнопку 'Нет кода':",
                                   reply_markup=get_barcode_menu())

@bot.callback_query_handler(func=lambda call: call.data.startswith("logs_"))
async def handle_logs_callback(call):
    user_id = call.from_user.id
    state = USER_STATES.get(user_id, {})
    action = call.data

    now = datetime.now()

    if action == "logs_today":
        date_from = now.replace(hour=0, minute=0, second=0, microsecond=0)
        date_to = now
    elif action == "logs_yesterday":
        date_from = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        date_to = (now - timedelta(days=1)).replace(hour=23, minute=59, second=59)
    elif action == "logs_week":
        date_from = now - timedelta(days=7)
        date_to = now
    elif action == "logs_month":
        date_from = now - timedelta(days=30)
        date_to = now
    elif action == "logs_3month":
        date_from = now - timedelta(days=90)
        date_to = now
    elif action == "logs_6month":
        date_from = now - timedelta(days=180)
        date_to = now
    elif action == "logs_12month":
        date_from = now - timedelta(days=365)
        date_to = now
    elif action == "logs_manual":
        await handle_admin_logs(bot, user_id, state)
        await bot.answer_callback_query(call.id)
        return
    else:
        await bot.answer_callback_query(call.id, "❌ Неизвестная команда")
        return

    await handle_admin_logs(bot, user_id, state, date_from=date_from, date_to=date_to)
    await bot.answer_callback_query(call.id)


# --- Функция для показа меню действий ---
async def send_action_menu(user_id):
    state = get_state(user_id)
    if state["role"] == "admin":
        await bot.send_message(user_id, f"Выберите действие:", reply_markup=get_admin_menu())
    else:
        await bot.send_message(user_id, f"Выберите действие:", reply_markup=get_user_menu())

# --- Точка входа ---
async def main():
    print("Бот запущен и следит за временем...")
    notifier.start_notifier(bot, GROUP_CHAT_ID, THREAD_ID)
    await bot.polling()

if __name__ == "__main__":
    asyncio.run(main())
