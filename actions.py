# actions.py

from telebot.async_telebot import AsyncTeleBot
from db import get_all_cartridge_types, get_stock_grouped_by_warehouse
from ui.menu import get_cartridge_inline_keyboard
# Эти функции пока используют только user_id и bot, потом можно будет расширить

async def handle_admin_income(bot: AsyncTeleBot, user_id: int):
    try:
        keyboard = get_cartridge_inline_keyboard()
        await bot.send_message(user_id, f"Выберите модель картриджа: ", reply_markup=keyboard)
    except Exception as e:
        await bot.send_message(user_id, f"Ошибка при приходе: {e}")

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

