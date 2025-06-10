from pyrogram import Client, filters
from config import API_ID, API_HASH, BOT_TOKEN
from handlers import start, session, broadcast

bot = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

start.init(bot)
session.init(bot)
broadcast.init(bot)

bot.run()
