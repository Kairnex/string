from pyrogram import filters
from pyrogram.types import CallbackQuery, Message
from config import ADMINS
from database import get_all_users

pending_broadcast = {}

def init(app):
    @app.on_callback_query(filters.regex("broadcast"))
    async def ask_broadcast(_, cq: CallbackQuery):
        if cq.from_user.id not in ADMINS:
            await cq.answer("Unauthorized", show_alert=True)
            return
        pending_broadcast[cq.from_user.id] = True
        await cq.message.edit("📢 Send your broadcast message:")

    @app.on_message(filters.private & filters.text)
    async def do_broadcast(_, msg: Message):
        if msg.from_user.id not in pending_broadcast:
            return

        del pending_broadcast[msg.from_user.id]
        count = 0
        for user in get_all_users():
            try:
                await _.send_message(user['user_id'], msg.text)
                count += 1
            except:
                pass
        await msg.reply(f"✅ Message sent to {count} users.")
