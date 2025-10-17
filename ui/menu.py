from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from db import get_all_cartridge_types  # импорт из твоего db.py

def get_warehouse_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(KeyboardButton("🏬 Невская"), KeyboardButton("🏬 Новороссийская"))
    markup.row(KeyboardButton("❓ Помощь"), KeyboardButton("🚪 Выйти"))
    return markup

def get_admin_menu():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        KeyboardButton("📤 Расход"),
        KeyboardButton("📥 Приход"),
        KeyboardButton("📊 Складской запас"),
        KeyboardButton("🚪 Выйти")
    )
    return keyboard

def get_user_menu():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        KeyboardButton("📤 Расход"),
        KeyboardButton("🚪 Выйти")
    )
    return keyboard

def get_cartridge_inline_keyboard():
    """
    Возвращает инлайн-клавиатуру с типами картриджей из базы.
    Используется для выбора модели в приходе/расходе.
    """
    types = get_all_cartridge_types()
    markup = InlineKeyboardMarkup(row_width=3)

    for model in types:
        btn = InlineKeyboardButton(text=model, callback_data=f"cartridge:{model}")
        markup.add(btn)

    return markup
