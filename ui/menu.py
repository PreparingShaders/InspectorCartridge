from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from db import get_all_cartridge_types  # импорт из твоего db.py

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
    """
    Возвращает инлайн-клавиатуру с типами картриджей из базы.
    Каждая строка содержит 2 кнопки. Внизу добавлена кнопка 'Назад'.
    """
    types = get_all_cartridge_types()
    markup = InlineKeyboardMarkup()

    # Группируем модели по 2 для двух колонок
    for i in range(0, len(types), 2):
        pair = types[i:i+2]
        buttons = [InlineKeyboardButton(text=model, callback_data=f"cartridge:{model}") for model in pair]
        markup.row(*buttons)  # добавляем ряд с 1 или 2 кнопками

    return markup

