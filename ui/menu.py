from telebot.types import ReplyKeyboardMarkup, KeyboardButton

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
        KeyboardButton("🚪 Выйти"),
        KeyboardButton("❓ Помощь")
    )
    return keyboard
