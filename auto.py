
from pyrogram import Client, filters
from dotenv import load_dotenv
import os

load_dotenv()

api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")

app = Client("userbot_session", api_id=api_id, api_hash=api_hash)

AUTO_REPLY = "👋 Hi! I'm away right now or may be no more available here. Will reply later if..."
@app.on_message(filters.private & ~filters.me)
async def auto_reply(client, message):
    await message.reply_text(AUTO_REPLY)

app.run()
