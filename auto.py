from pyrogram import Client, filters
from dotenv import load_dotenv
import os
import asyncio
import google.generativeai as genai

# Load environment variables
load_dotenv()
api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
gemini_api_key = os.getenv("GEMINI_API_KEY")

# Configure Gemini
genai.configure(api_key=gemini_api_key)
model = genai.GenerativeModel('gemini-pro')

# Initialize Pyrogram Client
app = Client("userbot_session", api_id=api_id, api_hash=api_hash)

# Track status and pending tasks
is_away = False
pending_tasks = {}

# Get AI response safely
def get_ai_response(prompt: str) -> str:
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception:
        return "Sorry, I couldn't generate a response right now."

# Delayed reply logic
async def delayed_reply(client, message):
    await asyncio.sleep(120)  # 2 minutes
    reply_text = await asyncio.to_thread(get_ai_response, message.text)
    await message.reply_text(reply_text)

# Command: /away to set status
@app.on_message(filters.me & filters.command("away"))
async def set_away(client, message):
    global is_away
    is_away = True
    await message.reply("✅ Status set to *Away*. AI will auto-reply after 2 minutes.")

# Command: /back to go online
@app.on_message(filters.me & filters.command("back"))
async def set_back(client, message):
    global is_away
    is_away = False
    await message.reply("🟢 Status set to *Available*. AI auto-replies are disabled.")

# Auto-reply handler
@app.on_message(filters.private & ~filters.me)
async def handle_message(client, message):
    global is_away
    if not is_away:
        return  # Do nothing if user is available

    chat_id = message.chat.id

    # Cancel any existing reply for this user
    if chat_id in pending_tasks:
        pending_tasks[chat_id].cancel()

    # Schedule new reply
    task = asyncio.create_task(delayed_reply(client, message))
    pending_tasks[chat_id] = task

app.run()
