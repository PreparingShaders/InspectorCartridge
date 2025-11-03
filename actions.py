# actions.py

from telebot.async_telebot import AsyncTeleBot
from db import get_all_cartridge_types, get_stock_grouped_by_warehouse, get_transactions_by_period
from ui.menu import get_cartridge_inline_keyboard, get_logs_pagination_markup
from datetime import datetime
import aiosqlite
import random

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

def chunk_logs(logs, size=3):
    """Разбивает список логов на страницы по size записей."""
    for i in range(0, len(logs), size):
        yield logs[i:i + size]


async def handle_admin_logs(bot: AsyncTeleBot, user_id: int, state: dict, text: str = None,
                            date_from=None, date_to=None, page: int = 0):
    if date_from and date_to:
        logs = get_transactions_by_period(date_from, date_to)

        if not logs:
            await bot.send_message(user_id, f"📭 Операции с {date_from.date()} по {date_to.date()} не найдены.")
            state["step"] = "awaiting_action"
            return

        # --- Разбиваем на страницы ---
        page_size = 3
        pages = list(chunk_logs(logs, page_size))
        total_pages = len(pages)

        # ❗ УДАЛЯЕМ строку page = 0
        # page = 0  # <-- убери эту строку

        # --- Проверяем, не вышли ли за пределы ---
        if page < 0:
            page = 0
        elif page >= total_pages:
            page = total_pages - 1

        # --- Формируем текст для выбранной страницы ---
        header = f"📜 Операции с {date_from.date()} по {date_to.date()}:\n\n"
        message = header

        for date, warehouse, model, barcode, operation, user, comment in pages[page]:
            if isinstance(date, str):
                date_str = date.split()[0]
            else:
                date_str = date.strftime("%d.%m.%Y")

            message += (
                f"📅 {date_str}\n"
                f"🏬 {warehouse}\n"
                f"🖨 {model} (🆔{barcode})\n"
                f"⚙️ {operation.capitalize()}\n"
                f"👤 {user}\n"
                f"💬 {comment or '—'}\n"
                f"━━━━━━━━━━━━━━━\n\n"
            )

        # --- Добавляем кнопки пагинации ---
        markup = get_logs_pagination_markup(
            page=page,
            total_pages=total_pages,
            date_from_ts=date_from.timestamp(),
            date_to_ts=date_to.timestamp()
        )

        # 🔧 Если это первая страница — отправляем новое сообщение
        # 🔧 Если переключаем страницу — редактируем старое
        if "last_logs_msg_id" in state:
            try:
                await bot.edit_message_text(
                    message,
                    chat_id=user_id,
                    message_id=state["last_logs_msg_id"],
                    reply_markup=markup
                )
            except Exception:
                # если редактирование не удалось (например, сообщение удалено) — отправляем новое
                msg = await bot.send_message(user_id, message, reply_markup=markup)
                state["last_logs_msg_id"] = msg.message_id
        else:
            msg = await bot.send_message(user_id, message, reply_markup=markup)
            state["last_logs_msg_id"] = msg.message_id

        state["step"] = "awaiting_action"
        return


    # --- остальное без изменений ---
    step = state.get("step")

    if step not in ("awaiting_logs_from", "awaiting_logs_to"):
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
            state["step"] = "awaiting_action"
            await bot.send_message(user_id, "⚠️ Что-то пошло не так. Попробуйте заново.")
            return

        if date_to < date_from:
            await bot.send_message(user_id, "❌ Дата окончания не может быть раньше даты начала. Попробуйте снова.")
            return

        await handle_admin_logs(bot, user_id, state, date_from=date_from, date_to=date_to)


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


async def notify_low_stock(bot: AsyncTeleBot, group_id: int, warehouse_id: int, cartridge_type_id: int, thread_id: int = None):
    """
    Проверяет остаток картриджей на складе и отправляет сообщение в группу (или ветку), если остаток < 3.
    Сообщение выбирается случайным образом из набора шаблонов.
    """
    async with aiosqlite.connect("inspector_SQLite.db") as db:
        # Получаем остаток
        async with db.execute("""
            SELECT SUM(quantity) 
            FROM transactions
            WHERE warehouse_id=? AND cartridge_type_id=?
        """, (warehouse_id, cartridge_type_id)) as cursor:
            row = await cursor.fetchone()
            total = row[0] or 0

        # Получаем название склада
        async with db.execute("SELECT name FROM warehouses WHERE id=?", (warehouse_id,)) as cursor:
            warehouse_row = await cursor.fetchone()
            warehouse_name = warehouse_row[0] if warehouse_row else f"ID {warehouse_id}"

        # Получаем модель картриджа
        async with db.execute("SELECT model FROM cartridge_types WHERE id=?", (cartridge_type_id,)) as cursor:
            model_row = await cursor.fetchone()
            model_name = model_row[0] if model_row else f"ID {cartridge_type_id}"

    # --- Проверяем критический уровень ---
    if total <= 5:
        # Набор сообщений для выбора
        messages = [
            (
                "👮‍♂️ Inspector на связи!\n"
                f"⚠️ Я тут не дремлю и заметил подозрительное движение на складе *{warehouse_name}*.\n"
                f"Картридж *{model_name}* тает на глазах — осталось всего {total} шт! 😨\n"
                f"Советую взять ситуацию на карандаш ✏️ и восполнить запас, пока не поздно!"
            ),
            (
                "🕵️‍♂️ Inspector докладывает:\n"
                f"На складе *{warehouse_name}* ситуация тревожная — картриджей *{model_name}* осталось всего {total} шт.\n"
                f"Пока ты читаешь это сообщение, может стать ещё меньше… 😏\n"
                f"Рекомендую пополнить запасы. Inspector бдит!"
            ),
            (
                "🚨 Inspector выходит из режима сна!\n"
                f"На складе *{warehouse_name}* почти закончились картриджи *{model_name}* — всего {total} шт!\n"
                f"Я не паникую, но если завтра кто-то не распечатает отчёт — я предупреждал 😎\n"
                f"Доставай карандаш ✏️ и добавляй заказ, пока не поздно!"
            ),
            (
                f"🌑 Inspector на связи. Ночь, кофе остыл, а картриджи на складе *{warehouse_name}* заканчиваются...\n"
                f"Осталось всего {total} шт. модели *{model_name}*.\n"
                f"Запах тревоги витает в воздухе. Я бы взял карандаш и записал это в журнал… пока не стало поздно. ☕️"
            ),
            (
                "🤖 Inspector сообщает: уровень чернил тревожно низкий!\n"
                f"Картриджей *{model_name}* на складе *{warehouse_name}* осталось {total} шт.\n"
                f"Мой алгоритм подсказывает — самое время пополнить запас, пока принтер не заплакал! 💧"
            )
        ]

        # Выбираем случайное сообщение
        message = random.choice(messages)

        await bot.send_message(
            group_id,
            message,
            message_thread_id=thread_id,
            parse_mode="Markdown"
        )

async def handle_user_expense(bot: AsyncTeleBot, user_id: int):
    try:
        keyboard = get_cartridge_inline_keyboard()
        await bot.send_message(user_id, f"Выберите модель картриджа: ", reply_markup=keyboard)
    except Exception as e:
        await bot.send_message(user_id, f"Ошибка при списании: {e}, {get_all_cartridge_types()}")

