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
