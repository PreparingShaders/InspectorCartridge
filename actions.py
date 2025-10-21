# actions.py

from telebot.async_telebot import AsyncTeleBot
from db import get_all_cartridge_types, get_stock_grouped_by_warehouse, get_transactions
from ui.menu import get_cartridge_inline_keyboard
# Эти функции пока используют только user_id и bot, потом можно будет расширить

async def handle_admin_income(bot: AsyncTeleBot, user_id: int):
    try:
        keyboard = get_cartridge_inline_keyboard()
        await bot.send_message(user_id, f"Выберите модель картриджа: ", reply_markup=keyboard)
    except Exception as e:
        await bot.send_message(user_id, f"Ошибка при приходе: {e}")

async def handle_admin_logs(bot: AsyncTeleBot, user_id: int, state: dict, text: str = None):
    """
    Если text=None — спрашиваем период.
    Если text — число — показываем операции за указанное количество дней.
    """
    if state.get("step") != "awaiting_logs_period":
        state["step"] = "awaiting_logs_period"
        await bot.send_message(user_id, "🕒 Укажите период в днях (например, 90):")
        return

    # Проверяем, что пользователь ввёл число
    if not text or not text.isdigit():
        await bot.send_message(user_id, "❌ Введите корректное число (например, 30).")
        return

    days = int(text)
    logs = get_transactions(days)

    if not logs:
        await bot.send_message(user_id, f"📭 За последние {days} дней операций не найдено.")
        state["step"] = "awaiting_action"
        return

    # Формируем сообщение
    message = f"📜 История операций за {days} дней:\n\n"
    for date, warehouse, model, operation, user, comment in logs:
        message += (
            f"📅 {date}\n"
            f"🏬 {warehouse}\n"
            f"🖨 {model}\n"
            f"⚙️ {operation.capitalize()} — {user}\n"
            f"💬 {comment or '—'}\n\n"
        )

    if len(message) > 4000:
        message = message[:4000] + "\n\n(Обрезано — слишком длинный список)"

    await bot.send_message(user_id, message)
    state["step"] = "awaiting_action"

async def handle_admin_stock(bot: AsyncTeleBot, user_id: int):
    stock_data = get_stock_grouped_by_warehouse()

    if not stock_data:
        await bot.send_message(user_id, "Нет данных о складе.")
        return

    # Группировка и форматирование данных
    message = "📊 Складской запас:\n\n"
    current_warehouse = None

    for warehouse, model, quantity in stock_data:
        if warehouse != current_warehouse:
            message += f"\n🏢 <b>{warehouse}</b>\n"
            current_warehouse = warehouse
        message += f"• {model}: {quantity} шт.\n"

    await bot.send_message(user_id, message, parse_mode="HTML")

async def handle_user_expense(bot: AsyncTeleBot, user_id: int):
    # Пока что просто пример записи
    try:
        keyboard = get_cartridge_inline_keyboard()
        await bot.send_message(user_id, f"Выберите модель картриджа: ", reply_markup=keyboard)
    except Exception as e:
        await bot.send_message(user_id, f"Ошибка при списании: {e}, {get_all_cartridge_types()}")

