# actions.py

from telebot.async_telebot import AsyncTeleBot
from db import get_all_cartridge_types
from ui.menu import get_cartridge_inline_keyboard
# Эти функции пока используют только user_id и bot, потом можно будет расширить

async def handle_admin_income(bot: AsyncTeleBot, user_id: int):
    try:
        keyboard = get_cartridge_inline_keyboard()
        await bot.send_message(user_id, f"Выберите модель картриджа: ", reply_markup=keyboard)
    except Exception as e:
        await bot.send_message(user_id, f"Ошибка при приходе: {e}")

async def handle_admin_stock(bot: AsyncTeleBot, user_id: int):
    await bot.send_message(user_id, "Функция запроса остатка пока не реализована")


async def handle_user_expense(bot: AsyncTeleBot, user_id: int):
    # Пока что просто пример записи
    try:
        add_transaction(
            barcode="TEST12345",
            warehouse_name="Невская",
            model="CF226X",
            quantity=1,
            operation_type="расход",
            user=f"user_{user_id}",
            comment="Списание через бота"
        )
        await bot.send_message(user_id, "Картридж списан (тестовая запись).")
    except Exception as e:
        await bot.send_message(user_id, f"Ошибка при списании: {e}, {get_all_cartridge_types()}")

