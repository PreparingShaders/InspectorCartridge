from telebot import types

def action_choice_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("➕ Приход", "➖ Расход")
    markup.add("Назад")
    return markup
