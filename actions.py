# actions.py

from telebot.async_telebot import AsyncTeleBot
from db import add_transaction

# Эти функции пока используют только user_id и bot, потом можно будет расширить

async def handle_admin_income(bot: AsyncTeleBot, user_id: int):
    try:
        add_transaction(
            barcode="TEST98765",
            warehouse_name="Невская",
            model="CF226X",
            quantity='4',
            operation_type="приход",
            user=f"admin_{user_id}",
            comment="Приход через бота"
        )
        await bot.send_message(user_id, "Приход записан (тестовая запись).")
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
        await bot.send_message(user_id, f"Ошибка при списании: {e}")

