# notifier.py
import aiocron
import secrets
from zoneinfo import ZoneInfo
from actions import handle_admin_stock

# --- вынесенный список сообщений ---
MESSAGES = [
    "Пятница, вечер… мысли уже о пиве и сериальчике 🍺📺, но Inspector не дремлет! Самое время глянуть, чем дышит склад 🧾",
    "Inspector ворвался с ревизией! 🔍 Пятница — не повод расслабляться. Картриджи сами себя не посчитают 😎",
    "Inspector докладывает: запахло пятницей и недостающими позициями 😅 Проверь остатки, пока все не убежали домой!",
    "Inspector следит даже по пятницам 🍺 — потому что чёрнила не знают выходных 🖤",
    "Пятница — отличный день, чтобы убедиться, что в понедельник не будет 'сюрпризов' от склада 😏",
    "Inspector: я не отдых, я контроль 💼 Проверим картриджи и спокойно в выходные!",
    "Inspector постучал в дверь склада... и не услышал картриджей 😬 Надо бы проверить!",
    "Кто-то думает о шашлыках, кто-то — о рыбалке 🎣 А Inspector думает о складе. Проверим остатки?",
    "Inspector на связи! 🕵️‍♂️ Пятница пятницей, но отчёт по складу сам себя не напишет 📊",
    "Пока все ушли за пивом, Inspector пошёл за порядком 😎 Время сверить картриджи!"
]

_last_message = None  # хранит предыдущее сообщение, чтобы не повторять подряд


def start_notifier(bot, group_id, thread_id):
    @aiocron.crontab('30 16 * * FRI', tz=ZoneInfo('Europe/Moscow'))  # каждую минуту для теста
    async def scheduled_notify():
        global _last_message

        # выбираем сообщение, не совпадающее с предыдущим
        message = secrets.choice(MESSAGES)
        while message == _last_message:
            message = secrets.choice(MESSAGES)
        _last_message = message

        print(f"[CRON] {message}")
        await bot.send_message(group_id, message, message_thread_id=thread_id)
        await handle_admin_stock(bot, group_id, thread_id)
