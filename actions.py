# actions.py

from telebot.async_telebot import AsyncTeleBot
from db import get_all_cartridge_types, get_stock_grouped_by_warehouse, get_transactions_by_period
from ui.menu import get_cartridge_inline_keyboard
from datetime import datetime
# Эти функции пока используют только user_id и bot, потом можно будет расширить

def parse_date(text: str):
    try:
        return datetime.strptime(text.strip(), "%d.%m.%Y")
    except ValueError as e:
        print(f"[DEBUG] Ошибка разбора даты: {e}")
        return None

async def handle_admin_income(bot: AsyncTeleBot, user_id: int):
    try:
        keyboard = get_cartridge_inline_keyboard()
        await bot.send_message(user_id, f"Выберите модель картриджа: ", reply_markup=keyboard)
    except Exception as e:
        await bot.send_message(user_id, f"Ошибка при приходе: {e}")

async def handle_admin_logs(bot: AsyncTeleBot, user_id: int, state: dict, text: str = None):
    step = state.get("step")

    if step != "awaiting_logs_from" and step != "awaiting_logs_to":
        # Первый шаг — запрос даты начала
        state["step"] = "awaiting_logs_from"
        await bot.send_message(user_id, "📅 Введите дату начала сбора логов (в формате ДД.ММ.ГГГГ):")
        return

    if step == "awaiting_logs_from":
        date_from = parse_date(text)
        if not date_from:
            await bot.send_message(user_id, "❌ Некорректный формат даты. Введите дату в формате ДД.ММ.ГГГГ.")
            return
        state["logs_from"] = date_from
        state["step"] = "awaiting_logs_to"
        await bot.send_message(user_id, "📅 Теперь введите дату окончания:")
        return

    if step == "awaiting_logs_to":
        date_to = parse_date(text)
        if not date_to:
            await bot.send_message(user_id, "❌ Некорректный формат даты. Введите дату в формате ДД.ММ.ГГГГ.")
            return

        date_from = state.get("logs_from")
        if not date_from:
            # На всякий случай — сброс состояния
            state["step"] = "awaiting_action"
            await bot.send_message(user_id, "⚠️ Что-то пошло не так. Попробуйте заново.")
            return

        if date_to < date_from:
            await bot.send_message(user_id, "❌ Дата окончания не может быть раньше даты начала. Попробуйте снова.")
            return

        # Получаем операции из БД
        logs = get_transactions_by_period(date_from, date_to)
        if not logs:
            await bot.send_message(user_id, f"📭 Операции с {date_from.date()} по {date_to.date()} не найдены.")
            state["step"] = "awaiting_action"
            return

        # Формируем сообщение
        message = f"📜 Операции с {date_from.date()} по {date_to.date()}:\n\n"
        for date, warehouse, model, barcode, operation, user, comment in logs:
            message += (
                f"📅 {date}\n"
                f"🏬 {warehouse}\n"
                f"🖨  {model} 🆔 {barcode}\n"
                f"⚙️ {operation.capitalize()} — {user}\n"
                f"💬 {comment or '—'}\n\n"
            )

        if len(message) > 4000:
            message = message[:4000] + "\n\n(Обрезано — слишком длинный список)"

        await bot.send_message(user_id, message)
        state["step"] = "awaiting_action"
        state.pop("logs_from", None)
        return


async def handle_admin_stock(bot: AsyncTeleBot, user_id: int, thread_id: int = None):
    stock_data = get_stock_grouped_by_warehouse()

    if not stock_data:
        await bot.send_message(user_id, "Нет данных о складе.", message_thread_id=thread_id)
        return

    message = "📊 Складской запас:\n\n"
    current_warehouse = None
    totals = {}

    for warehouse, model, quantity in stock_data:
        if warehouse != current_warehouse:
            message += f"\n🏢 <b>{warehouse}</b>\n"
            current_warehouse = warehouse

        message += f"🖨 {model}: {quantity} шт.\n"
        totals[model] = totals.get(model, 0) + quantity

    message += "\n📦 <b>Общий остаток по всем складам:</b>\n"
    for model, total_qty in totals.items():
        message += f"🖨 {model}: {total_qty} шт.\n"

    # Добавляем thread_id, если он указан
    if thread_id:
        await bot.send_message(user_id, message, parse_mode="HTML", message_thread_id=thread_id)
    else:
        await bot.send_message(user_id, message, parse_mode="HTML")


async def handle_user_expense(bot: AsyncTeleBot, user_id: int):
    try:
        keyboard = get_cartridge_inline_keyboard()
        await bot.send_message(user_id, f"Выберите модель картриджа: ", reply_markup=keyboard)
    except Exception as e:
        await bot.send_message(user_id, f"Ошибка при списании: {e}, {get_all_cartridge_types()}")

