from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from database import save_user

def init(app):
    @app.on_message(filters.command("start"))
    async def start(_, message: Message):
        save_user(message.from_user)
        await message.reply(
            f"👋 Hello {message.from_user.first_name}!\nWelcome to the Session Generator Bot.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🌐 Pyrogram", callback_data="gen_pyrogram")],
                [InlineKeyboardButton("⚡ Telethon", callback_data="gen_telethon")],
                [InlineKeyboardButton("📣 Broadcast", callback_data="broadcast")]
            ])
        )
