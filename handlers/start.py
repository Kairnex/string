from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import UserNotParticipant
from database import save_user
from config import REQUIRED_CHANNEL, REQUIRED_GROUP

def init(app):
    async def is_user_member(client, user_id):
        try:
            await client.get_chat_member(REQUIRED_CHANNEL, user_id)
            await client.get_chat_member(REQUIRED_GROUP, user_id)
            return True
        except UserNotParticipant:
            return False
        except Exception:
            return False

    @app.on_message(filters.command("start") & filters.private)
    async def start(_, message: Message):
        user_id = message.from_user.id
        if not await is_user_member(_, user_id):
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{REQUIRED_CHANNEL}")],
                [InlineKeyboardButton("✅ I've Joined", callback_data="check_subscription")]
            ])
            await message.reply(
                "**🔐 Access Denied!**\n\nPlease join the required **channel**to use this bot.",
                reply_markup=keyboard
            )
            return

        save_user(message.from_user)
        await message.reply(
            f"👋 Hello {message.from_user.first_name}!\nWelcome to the Session Generator Bot.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🌐 Pyrogram", callback_data="gen_pyrogram")],
                [InlineKeyboardButton("⚡ Telethon", callback_data="gen_telethon")]
            ])
        )

    @app.on_callback_query(filters.regex("check_subscription"))
    async def check_subscription_callback(client, callback_query: CallbackQuery):
        if await is_user_member(client, callback_query.from_user.id):
            await callback_query.message.edit("✅ You're now verified! Use /start to continue.")
        else:
            await callback_query.answer("❌ You're still not joined both. Please join and try again.", show_alert=True)
