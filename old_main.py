#!/usr/bin/python
import asyncio
import os
import sqlite3
from datetime import datetime
from io import BytesIO

from telebot.async_telebot import AsyncTeleBot
from telebot import types

# Попытка импортировать pyzbar/Pillow — если не получится, перейдём в ручной режим
HAS_PYZBAR = True
try:
    from PIL import Image
    from pyzbar.pyzbar import decode
except Exception:
    HAS_PYZBAR = False

bot = AsyncTeleBot(os.environ["TELEGRAM_TESTBOT"])
DB_FILE = "cartridges.db"


# --------- ИНИЦИАЛИЗАЦИЯ БАЗЫ ---------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    # Оставляем твою старую таблицу cartridges & history
    cur.execute("""
        CREATE TABLE IF NOT EXISTS cartridges (
            name TEXT PRIMARY KEY,
            qty INTEGER NOT NULL DEFAULT 0
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            name TEXT NOT NULL,
            qty INTEGER NOT NULL,
            user TEXT,
            timestamp TEXT NOT NULL
        )
    """)
    # Новая таблица для сопоставления barcode -> name
    cur.execute("""
        CREATE TABLE IF NOT EXISTS barcodes (
            barcode TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            UNIQUE(barcode)
        )
    """)
    conn.commit()
    conn.close()


# --------- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ (твои старые) ---------
def add_cartridge(name, qty, user):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO cartridges(name, qty)
        VALUES(?, ?)
        ON CONFLICT(name) DO UPDATE SET qty = qty + ?
    """, (name, qty, qty))
    cur.execute("""
        INSERT INTO history(action, name, qty, user, timestamp)
        VALUES(?, ?, ?, ?, ?)
    """, ("add", name, qty, user, datetime.now().isoformat(timespec="seconds")))
    conn.commit()
    conn.close()


def use_cartridge(name, qty, user):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT qty FROM cartridges WHERE name=?", (name,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return "❌ Картридж не найден."
    if row[0] < qty:
        conn.close()
        return f"⚠️ Недостаточно на складе. Остаток: {row[0]}"
    cur.execute("UPDATE cartridges SET qty = qty - ? WHERE name=?", (qty, name))
    cur.execute("""
        INSERT INTO history(action, name, qty, user, timestamp)
        VALUES(?, ?, ?, ?, ?)
    """, ("use", name, qty, user, datetime.now().isoformat(timespec="seconds")))
    conn.commit()
    conn.close()
    return f"📤 Списано {qty} шт. *{name}*."


def get_status():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT name, qty FROM cartridges ORDER BY name")
    rows = cur.fetchall()
    conn.close()
    if not rows:
        return "📭 Склад пуст."
    return "\n".join(f"• {name}: {qty}" for name, qty in rows)


def get_history(limit=10):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        SELECT action, name, qty, user, timestamp
        FROM history ORDER BY id DESC LIMIT ?
    """, (limit,))
    rows = cur.fetchall()
    conn.close()
    if not rows:
        return "🕓 История пуста."
    lines = []
    for action, name, qty, user, timestamp in rows:
        icon = "➕" if action == "add" else "➖"
        who = f" ({user})" if user else ""
        lines.append(f"{icon} {timestamp}: {name} — {qty} шт{who}")
    return "\n".join(lines)


# --------- НОВЫЕ ВСПОМОГАТЕЛЬНЫЕ ДЛЯ BARCODE ---------
def find_name_by_barcode(barcode):
    """
    Вернёт имя картриджа (name) или None
    """
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT name FROM barcodes WHERE barcode = ?", (barcode,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None


def add_barcode_mapping(barcode, name):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO barcodes(barcode, name) VALUES(?, ?)", (barcode, name))
    conn.commit()
    conn.close()


# --------- UI: главное меню ---------
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📷 Сканировать", "🖊 Ввести штрих-код")
    markup.row("📋 Остаток", "🕓 История")
    return markup


# --------- ЧТЕНИЕ ШТРИХКОДА (если pyzbar доступен) ---------
def read_barcode_from_bytes(image_bytes):
    if not HAS_PYZBAR:
        return None
    try:
        img = Image.open(BytesIO(image_bytes))
        codes = decode(img)
        if not codes:
            return None
        return codes[0].data.decode("utf-8")
    except Exception:
        return None


# --------- СОСТОЯНИЕ ПОЛЬЗОВАТЕЛЯ (workflow) ---------
# user_state[chat_id] = {
#    'step': 'idle'|'await_scan'|'await_manual'|'await_new_name'|'await_new_qty'|'await_action_qty',
#    'barcode': str or None,
#    'name': str or None,
#    'action': 'add'|'use' or None
# }
user_state = {}


# --------- ХЭНДЛЕРЫ ---------
@bot.message_handler(commands=["start", "help"])
async def start(message):
    text = "📦 Учёт картриджей.\nНажми «Сканировать» и пришли фото штрих-кода или выбери «Ввести штрих-код»."
    if not HAS_PYZBAR:
        text += "\n\n⚠️ Внимание: на сервере не установлена библиотека распознавания штрих-кодов (zbar/pyzbar). Отправка фото не будет работать, используй «Ввести штрих-код» или установи zbar (см. инструкцию)."
    await bot.send_message(message.chat.id, text, reply_markup=main_menu())


@bot.message_handler(func=lambda m: m.text == "📋 Остаток")
async def show_status(message):
    await bot.send_message(message.chat.id, "📋 Текущий остаток:\n\n" + get_status())


@bot.message_handler(func=lambda m: m.text == "🕓 История")
async def show_history(message):
    await bot.send_message(message.chat.id, "📜 Последние операции:\n\n" + get_history())


@bot.message_handler(func=lambda m: m.text == "📷 Сканировать")
async def cmd_scan(message):
    # проверим, доступно ли pyzbar
    if not HAS_PYZBAR:
        # подсказка по установке zbar
        help_text = (
            "⚠️ Распознавание по фото недоступно — отсутствует системная библиотека zbar или Python-пакет pyzbar.\n\n"
            "Для macOS (Homebrew):\n  brew install zbar\n\n"
            "Для Ubuntu/Debian:\n  sudo apt install libzbar0\n\n"
            "После установки перезапусти виртуальное окружение и попробуй снова.\n\n"
            "Пока ставить zbar не будем — введи штрих-код вручную через кнопку «🖊 Ввести штрих-код»."
        )
        await bot.send_message(message.chat.id, help_text)
        return

    # переводим в режим ожидания фото
    user_state[message.chat.id] = {'step': 'await_scan', 'barcode': None, 'name': None, 'action': None}
    await bot.send_message(message.chat.id, "📸 Пришли фото штрих-кода картриджа (лучше крупным планом).", reply_markup=types.ReplyKeyboardRemove())


@bot.message_handler(func=lambda m: m.text == "🖊 Ввести штрих-код")
async def cmd_manual_start(message):
    user_state[message.chat.id] = {'step': 'await_manual', 'barcode': None, 'name': None, 'action': None}
    await bot.send_message(message.chat.id, "Введите штрих-код (текстом):", reply_markup=types.ReplyKeyboardRemove())


# Обработка фото (если ожидаем скан)
@bot.message_handler(content_types=['photo'])
async def handle_photo(message):
    st = user_state.get(message.chat.id)
    if not st or st.get('step') != 'await_scan':
        return  # фото пришло вне контекста сканирования — игнорируем

    # берем максимальное по размеру фото
    photo = message.photo[-1]
    file_info = await bot.get_file(photo.file_id)
    file_bytes = await bot.download_file(file_info.file_path)
    barcode = read_barcode_from_bytes(file_bytes)

    if not barcode:
        # не распознали — предложим ввести вручную
        st['step'] = 'await_manual'
        await bot.send_message(message.chat.id,
                               "Не удалось распознать штрих-код с фото. Введи штрих-код вручную или пришли другое фото.",
                               reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add("Назад"))
        return

    # распознали штрих-код
    st['barcode'] = barcode
    name = find_name_by_barcode(barcode)
    if name:
        st['name'] = name
        st['step'] = 'await_action_choice'
        # предлагаем действия
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("➕ Приход", "➖ Расход")
        markup.add("Назад")
        # узнаем текущий остаток (если есть)
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("SELECT qty FROM cartridges WHERE name=?", (name,))
        r = cur.fetchone()
        qty = r[0] if r else 0
        conn.close()
        await bot.send_message(message.chat.id,
                               f"🔎 Найдено: *{name}* ({barcode})\nОстаток: *{qty}* шт.\nВыберите действие:",
                               parse_mode="Markdown", reply_markup=markup)
    else:
        # не найден — предложим добавить (сразу имя)
        st['step'] = 'await_new_name'
        st['barcode'] = barcode
        await bot.send_message(message.chat.id,
                               f"ℹ️ Штрих-код *{barcode}* не найден в базе. Введите название картриджа для добавления:",
                               parse_mode="Markdown",
                               reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add("Назад"))


# Текстовый обработчик — универсальный (в зависимости от состояния)
@bot.message_handler(func=lambda m: True)
async def handle_text(message):
    text = (message.text or "").strip()
    st = user_state.get(message.chat.id)

    # кнопка "Назад" — вернуть в главное меню и сбросить состояние
    if text.lower() == "назад":
        user_state.pop(message.chat.id, None)
        await bot.send_message(message.chat.id, "Отмена. Главное меню:", reply_markup=main_menu())
        return

    # если нет состояния — просто показать меню
    if not st:
        await bot.send_message(message.chat.id, "Выберите действие:", reply_markup=main_menu())
        return

    step = st.get('step')

    # manual barcode input
    if step == 'await_manual':
        barcode = text
        st['barcode'] = barcode
        name = find_name_by_barcode(barcode)
        if name:
            st['name'] = name
            st['step'] = 'await_action_choice'
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add("➕ Приход", "➖ Расход")
            markup.add("Назад")
            # get qty
            conn = sqlite3.connect(DB_FILE)
            cur = conn.cursor()
            cur.execute("SELECT qty FROM cartridges WHERE name=?", (name,))
            r = cur.fetchone()
            qty = r[0] if r else 0
            conn.close()
            await bot.send_message(message.chat.id,
                                   f"🔎 Найдено: *{name}* ({barcode})\nОстаток: *{qty}* шт.\nВыберите действие:",
                                   parse_mode="Markdown", reply_markup=markup)
        else:
            st['step'] = 'await_new_name'
            await bot.send_message(message.chat.id, f"Штрих-код {barcode} не найден. Введите название нового картриджа:", reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add("Назад"))
        return

    # ввод названия для нового картриджа
    if step == 'await_new_name':
        st['name'] = text
        st['step'] = 'await_new_qty'
        await bot.send_message(message.chat.id, "Введите количество (целое число):", reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add("Назад"))
        return

    # ввод количества для нового картриджа
    if step == 'await_new_qty':
        try:
            qty = int(text)
            if qty < 0:
                raise ValueError()
        except ValueError:
            await bot.send_message(message.chat.id, "⚠️ Введите корректное неотрицательное целое число.")
            return
        barcode = st.get('barcode')
        name = st.get('name')
        user = message.from_user.username or message.from_user.first_name
        # добавляем новую запись в cartridges и маппинг barcode->name
        add_cartridge(name, qty, user)
        add_barcode_mapping(barcode, name)
        await bot.send_message(message.chat.id, f"✅ Картридж *{name}* ({barcode}) добавлен: {qty} шт.", parse_mode="Markdown", reply_markup=main_menu())
        user_state.pop(message.chat.id, None)
        return

    # выбор действия (после найденного штрих-кода)
    if step == 'await_action_choice':
        if text == "➕ Приход":
            st['action'] = 'add'
            st['step'] = 'await_action_qty'
            await bot.send_message(message.chat.id, "Введите количество для прихода:", reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add("Назад"))
            return
        if text == "➖ Расход":
            st['action'] = 'use'
            st['step'] = 'await_action_qty'
            await bot.send_message(message.chat.id, "Введите количество для списания:", reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add("Назад"))
            return
        await bot.send_message(message.chat.id, "Нажмите одну из кнопок: ➕ Приход или ➖ Расход.", reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add("➕ Приход", "➖ Расход").add("Назад"))
        return

    # ввод количества для выбранного действия
    if step == 'await_action_qty':
        try:
            qty = int(text)
            if qty <= 0:
                raise ValueError()
        except ValueError:
            await bot.send_message(message.chat.id, "⚠️ Введите корректное целое положительное число.")
            return

        name = st.get('name')
        action = st.get('action')
        user = message.from_user.username or message.from_user.first_name
        if action == 'add':
            add_cartridge(name, qty, user)
            await bot.send_message(message.chat.id, f"✅ Добавлено {qty} шт. *{name}*.", parse_mode="Markdown", reply_markup=main_menu())
        else:
            res = use_cartridge(name, qty, user)
            await bot.send_message(message.chat.id, res, parse_mode="Markdown", reply_markup=main_menu())
        user_state.pop(message.chat.id, None)
        return

    # fallback
    await bot.send_message(message.chat.id, "Неизвестное состояние. Возврат в меню.", reply_markup=main_menu())
    user_state.pop(message.chat.id, None)


# --------- ЗАПУСК ---------
if __name__ == "__main__":
    init_db()
    print("🤖 Бот запущен...")
    asyncio.run(bot.polling())
