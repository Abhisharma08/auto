
# from pyrogram import Client, filters
# from dotenv import load_dotenv
# import os

# load_dotenv()

# api_id = int(os.getenv("API_ID"))
# api_hash = os.getenv("API_HASH")

# app = Client("userbot_session", api_id=api_id, api_hash=api_hash)

# AUTO_REPLY = "...........Hi.....Byee........"
# @app.on_message(filters.private & ~filters.me)
# async def auto_reply(client, message):
#     await message.reply_text(AUTO_REPLY)

# app.run()


from pyrogram import Client, filters
from dotenv import load_dotenv
import os
import google.generativeai as genai

# Load environment variables
load_dotenv()
api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
gemini_api_key = os.getenv("GEMINI_API_KEY")

# Initialize Gemini
genai.configure(api_key=gemini_api_key)
model = genai.GenerativeModel('gemini-pro')

# Initialize Pyrogram Client
app = Client("userbot_session", api_id=api_id, api_hash=api_hash)

# AI-Powered Auto-reply
@app.on_message(filters.private & ~filters.me)
async def auto_reply(client, message):
    user_msg = message.text

    try:
        response = model.generate_content(user_msg)
        reply_text = response.text
    except Exception as e:
        reply_text = "Sorry, I couldn't generate a response right now."

    await message.reply_text(reply_text)

app.run()
