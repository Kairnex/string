from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import UserNotParticipant
from database import save_user
from config import REQUIRED_CHANNEL

def init(app):

    # Check if the user is a member of the required channel
    async def is_user_member(client, user_id):
        try:
            await client.get_chat_member(REQUIRED_CHANNEL, user_id)
            return True
        except UserNotParticipant:
            return False
        except Exception:
            return False

    # Start command handler
    @app.on_message(filters.command("start") & filters.private)
    async def start(client, message: Message):
        user_id = message.from_user.id

        # If user is not a member, prompt to join
        if not await is_user_member(client, user_id):
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{REQUIRED_CHANNEL}")],
                [InlineKeyboardButton("✅ I've Joined", callback_data="check_subscription")]
            ])
            await message.reply(
                "**🔐 Access Denied!**\n\nPlease join the required **channel** to use this bot.",
                reply_markup=keyboard
            )
            return

        # If user is a member, proceed
        save_user(message.from_user)
        await message.reply(
            f"👋 Hello {message.from_user.first_name}!\nWelcome to the **Session Generator Bot**.\nChoose your preferred library:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🌐 Pyrogram", callback_data="gen_pyrogram")],
                [InlineKeyboardButton("⚡ Telethon", callback_data="gen_telethon")]
            ])
        )

    # Callback handler to re-check subscription
    @app.on_callback_query(filters.regex("check_subscription"))
    async def check_subscription_callback(client, callback_query: CallbackQuery):
        if await is_user_member(client, callback_query.from_user.id):
            await callback_query.message.edit("✅ You're now verified! Please send /start again to continue.")
        else:
            await callback_query.answer("❌ You're still not joined. Please join the channel and try again.", show_alert=True)
