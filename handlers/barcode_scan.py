from telebot.types import Message
from pyzbar.pyzbar import decode
from PIL import Image, ImageFilter, ImageOps, ImageEnhance
import io
from ui.menu import get_comment_menu


def init_barcode_handler(bot, get_state):
    @bot.message_handler(content_types=['photo'])
    async def handle_barcode_photo(message: Message):
        user_id = message.from_user.id
        state = get_state(user_id)

        if not state or state.get("step") != "awaiting_barcode":
            return

        # Получаем фото в лучшем качестве
        file_info = await bot.get_file(message.photo[-1].file_id)
        downloaded = await bot.download_file(file_info.file_path)
        image = Image.open(io.BytesIO(downloaded))

        # Преобразуем в серый, убираем шум
        image = image.convert("L")
        image = ImageOps.autocontrast(image)

        # --- 3 попытки декодирования ---
        attempts = [
            ("🔹 Базовая обработка", image),
            ("🔸 Повышенная резкость", image.filter(ImageFilter.SHARPEN)),
            ("🔸 Усиленный контраст", ImageEnhance.Contrast(image).enhance(2.5))
        ]

        decoded_objects = None
        for label, img_variant in attempts:
            decoded = decode(img_variant)
            if decoded:
                decoded_objects = decoded
                print(f"[INFO] Barcode decoded ({label}) для пользователя {user_id}")
                break  # если удалось — выходим из цикла

        # --- Если не удалось ---
        if not decoded_objects:
            await bot.send_message(
                user_id,
                "🚫 Не удалось распознать штрих-код после 3 попыток.\n"
                "Попробуйте сделать фото ближе и при хорошем освещении."
            )
            return

        # --- Если распознан ---
        barcode = decoded_objects[0].data.decode("utf-8")

        if barcode.isdigit() and len(barcode) == 13:
            state["barcode"] = barcode
            state["step"] = "awaiting_comment"
            await bot.send_message(
                user_id,
                f"✅ Штрих-код распознан: 🆔 {barcode}\n\n"
                "💬 Введите комментарий (например, имя пользователя, отдел, имя принтера и т.п.):",
                reply_markup=get_comment_menu()
            )
        else:
            await bot.send_message(
                user_id,
                f"⚠️ Распознанный код: {barcode}\nОн должен содержать ровно 13 цифр."
            )
