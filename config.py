import os

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")

ADMINS = list(map(int, os.getenv("ADMINS", "").split()))
ADMIN_ID = list(map(int, os.getenv("ADMIN_ID", "").split()))

LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID"))
REQUIRED_CHANNEL = os.getenv("REQUIRED_CHANNEL")
