from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from db import get_all_cartridge_types  # импорт из твоего db.py
import re


def get_warehouse_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(KeyboardButton( "🏬 Невская"), KeyboardButton("🏬 Новороссийская"))
    markup.row(KeyboardButton ("❓ Помощь"), KeyboardButton("📊 Складской запас"))
    markup.row(KeyboardButton("🚪 Выйти"))
    return markup

def get_admin_menu():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        KeyboardButton("📤 Расход"),
        KeyboardButton("📥 Приход"),
        KeyboardButton("📜 История операций"),
        KeyboardButton("◀️ Назад")
    )
    return keyboard

def get_user_menu():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        KeyboardButton("📤 Расход"),
        KeyboardButton("◀️ Назад")
    )
    return keyboard

def get_barcode_menu():
    """
    Возвращает клавиатуру с кнопкой 'Нет кода' и 'Назад' для ввода штрих-кода.
    """
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(KeyboardButton("Нет кода"), KeyboardButton("◀️ Назад"))
    return markup

def get_confirm_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(KeyboardButton("✅ Верно"), KeyboardButton("◀️ Назад"))
    return markup

def confirm_transaction():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("✅ Подтвердить"), KeyboardButton("◀️ Назад") )
    return markup

def get_after_operation_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.row(KeyboardButton("↩ Повторить"),KeyboardButton("📋 Меню"))
    return markup

def get_comment_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.row(KeyboardButton("◀️ Назад"))
    return markup

def get_cartridge_inline_keyboard():
    types = get_all_cartridge_types()  # функция, которая возвращает все модели
    markup = InlineKeyboardMarkup()

    # Функция для извлечения числа из модели
    def extract_number(model):
        match = re.search(r'\d+', model)
        return int(match.group()) if match else float('inf')

    # Сортируем список по числу
    types.sort(key=lambda x: (extract_number(x), x))

    # Разделяем на левый и правый столбцы
    mid = (len(types) + 1) // 2
    left_col = types[:mid]
    right_col = types[mid:]

    # Формируем ряды кнопок по 2: левый + правый
    for i in range(mid):
        buttons = [InlineKeyboardButton(text=left_col[i], callback_data=f"cartridge:{left_col[i]}")]
        if i < len(right_col):
            buttons.append(InlineKeyboardButton(text=right_col[i], callback_data=f"cartridge:{right_col[i]}"))
        markup.row(*buttons)

    return markup

def get_logs_keyboard():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🕐 Сегодня", callback_data="logs_today"),
        InlineKeyboardButton("📅 Вчера", callback_data="logs_yesterday"),
        InlineKeyboardButton("📆 7 дней", callback_data="logs_week"),
        InlineKeyboardButton("🗓 30 дней", callback_data="logs_month"),
        InlineKeyboardButton("🕰 3 месяца", callback_data="logs_3month"),
        InlineKeyboardButton("🕰 6 месяца", callback_data="logs_6month"),
        InlineKeyboardButton("🕰 12 месяцев", callback_data="logs_12month"),
        InlineKeyboardButton("🧾 Выбрать вручную", callback_data="logs_manual"),
        InlineKeyboardButton("📊 Выгрузить Excel", callback_data="export_excel")  # <-- новая кнопка

    )
    return kb

def get_logs_pagination_markup(page: int, total_pages: int, date_from_ts: float, date_to_ts: float):
    """
    Возвращает InlineKeyboardMarkup для навигации по страницам логов.
    callback_data формата: logs_page:{page}|{from_ts}|{to_ts}
    где from_ts и to_ts — UNIX timestamp (float or int).
    """
    kb = InlineKeyboardMarkup(row_width=3)
    buttons = []

    # Кнопка назад
    if page > 0:
        cb = f"logs_page:{page-1}|{int(date_from_ts)}|{int(date_to_ts)}"
        buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data=cb))

    # Статус (неактивная кнопка — можно не добавлять, но оставим для UX)
    buttons.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="logs_page_info"))

    # Кнопка вперёд
    if page < total_pages - 1:
        cb = f"logs_page:{page+1}|{int(date_from_ts)}|{int(date_to_ts)}"
        buttons.append(InlineKeyboardButton("➡️ Вперёд", callback_data=cb))

    # Добавляем ряд навигации (если только одна кнопка — она будет в центре)
    kb.row(*buttons)

    # Кнопка возврата в меню (всегда)
    kb.add(InlineKeyboardButton("📋 Меню", callback_data="back_to_menu"))

    return kb