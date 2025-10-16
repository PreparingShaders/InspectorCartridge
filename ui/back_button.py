from telebot import types

def back_markup():
    return types.ReplyKeyboardMarkup(resize_keyboard=True).add("Назад")
