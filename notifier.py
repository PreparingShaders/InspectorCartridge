# notifier.py

from actions import handle_admin_stock

async def notify_admin_stock(bot, group_chat_id, thread_id):
    await handle_admin_stock(bot, group_chat_id, thread_id)
