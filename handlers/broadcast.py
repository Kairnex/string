from pyrogram import filters, Client
from pyrogram.types import Message
from database import get_all_users
from config import ADMIN_ID
import asyncio

SHORT_DELAY = 0.5
LONG_DELAY = 5
BATCH_SIZE = 70

def init(app: Client):
    @app.on_message(filters.command("broadcast") & filters.user(ADMIN_ID))
    async def broadcast_message(client, message: Message):
        if not message.reply_to_message:
            return await message.reply("⚠️ Reply to the message you want to broadcast.")
        
        users = get_all_users()
        total = len(users)
        success = 0
        failed = 0

        status_msg = await message.reply(f"📢 Broadcasting to {total} users...")

        for index, user in enumerate(users, start=1):
            try:
                await client.copy_message(
                    chat_id=user["user_id"],
                    from_chat_id=message.chat.id,
                    message_id=message.reply_to_message.id
                )
                success += 1
            except Exception:
                failed += 1

            if index % BATCH_SIZE == 0:
                await asyncio.sleep(LONG_DELAY)
            else:
                await asyncio.sleep(SHORT_DELAY)

        await status_msg.edit(
            f"✅ Broadcast Completed\n\n👥 Total: {total}\n✅ Success: {success}\n❌ Failed: {failed}"
        )

    @app.on_message(filters.command("users") & filters.user(ADMIN_ID))
    async def show_users(client, message: Message):
        users = get_all_users()
        await message.reply(f"👥 Total users: {len(users)}")
