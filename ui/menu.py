from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from db import get_cartridge_types_for_model  # если она у тебя в db.py


def get_warehouse_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(KeyboardButton("🏬 Невская"), KeyboardButton("🏬 Новороссийская")),
    markup.row( KeyboardButton("❓ Помощь"), KeyboardButton("🚪 Выйти"),)
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

def get_cartridge_type_keyboard(action: str, model: str):
    types = get_cartridge_types_for_model(model)  # [(id, name), ...]
    if not types:
        return None

    markup = InlineKeyboardMarkup()
    for type_id, name in types:
        markup.add(InlineKeyboardButton(text=name, callback_data=f"{action}:{type_id}"))
    markup.add(InlineKeyboardButton("🔙 Отмена", callback_data="cancel"))
    return markup
