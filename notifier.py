# notifier.py
import aiocron
import secrets
from zoneinfo import ZoneInfo
from actions import handle_admin_stock

# --- вынесенный список сообщений ---
MESSAGES = [
    "Пятница, вечер… мысли уже о пиве и сериальчике 🍺📺, но Inspector не дремлет! Самое время глянуть, чем дышит склад 🧾\n",
    "Inspector ворвался с ревизией! 🔍 Пятница — не повод расслабляться. Картриджи сами себя не посчитают 😎\n",
    "Inspector докладывает: запахло пятницей и недостающими позициями 😅 Проверь остатки, пока все не убежали домой!\n",
    "Inspector следит даже по пятницам 🍺 — потому что чёрнила не знают выходных 🖤\n",
    "Пятница — отличный день, чтобы убедиться, что в понедельник не будет 'сюрпризов' от склада 😏\n",
    "Inspector: я не отдых, я контроль 💼 Проверим картриджи и спокойно в выходные!\n",
    "Inspector постучал в дверь склада... и не услышал картриджей 😬 Надо бы проверить!\n",
    "Кто-то думает о шашлыках, кто-то — о рыбалке 🎣 А Inspector думает о складе. Проверим остатки?\n",
    "Inspector на связи! 🕵️‍♂️ Пятница пятницей, но отчёт по складу сам себя не напишет 📊\n",
    "Пока все ушли за пивом, Inspector пошёл за порядком 😎 Время сверить картриджи!\n"
]

_last_message = None  # хранит предыдущее сообщение, чтобы не повторять подряд


def start_notifier(bot, group_id, thread_id):
    @aiocron.crontab('* * * * FRI', tz=ZoneInfo('Europe/Moscow'))  # каждую минуту для теста
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
