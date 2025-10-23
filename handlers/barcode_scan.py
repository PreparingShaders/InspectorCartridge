from telebot.types import Message
from pyzbar.pyzbar import decode
from PIL import Image
import io

def init_barcode_handler(bot, get_state):
    @bot.message_handler(content_types=['photo'])
    async def handle_barcode_photo(message: Message):
        user_id = message.from_user.id
        state = get_state(user_id)

        # Проверяем, на каком этапе находится пользователь
        if not state or state.get("step") != "awaiting_barcode":
            return  # игнорируем, если фото пришло не на нужном шаге

        # Получаем фото в наилучшем качестве
        file_info = await bot.get_file(message.photo[-1].file_id)
        downloaded = await bot.download_file(file_info.file_path)

        # Пытаемся распознать штрих-код
        image = Image.open(io.BytesIO(downloaded))
        decoded_objects = decode(image)

        if not decoded_objects:
            await bot.send_message(user_id, "🚫 Не удалось распознать штрих-код. Попробуйте ещё раз.")
            return

        barcode = decoded_objects[0].data.decode("utf-8")

        # Проверяем формат
        if barcode.isdigit() and len(barcode) == 13:
            state["barcode"] = barcode
            state["step"] = "awaiting_comment"
            await bot.send_message(user_id, f"✅ Штрих-код распознан: {barcode}\n\n💬 Введите комментарий:")
        else:
            await bot.send_message(user_id, f"⚠️ Распознанный код: {barcode}\nОн должен содержать 13 цифр.")
