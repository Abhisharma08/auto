from pyrogram import Client, filters
from dotenv import load_dotenv
import os
import asyncio
import google.generativeai as genai

# ------------ Config & Setup ------------
load_dotenv()

try:
    api_id = int(os.getenv("API_ID", "").strip())
except ValueError:
    api_id = None
api_hash = (os.getenv("API_HASH") or "").strip()
gemini_api_key = (os.getenv("GEMINI_API_KEY") or "").strip()

if not api_id or not api_hash:
    raise RuntimeError("API_ID/API_HASH missing or invalid in environment.")
if not gemini_api_key:
    raise RuntimeError("GEMINI_API_KEY missing in environment.")

genai.configure(api_key=gemini_api_key)

# Use a valid Gemini model name
# Common current names: "gemini-2.0-flash", "gemini-2.0-pro" (check your quota/enablement)
model = genai.GenerativeModel(model_name="gemini-2.0-flash")

# Pyrogram session (userbot)
app = Client("userbot_session", api_id=api_id, api_hash=api_hash)

# ------------ State ------------
is_away = False
pending_tasks: dict[int, asyncio.Task] = {}
REPLY_DELAY_SECONDS = 120  # 2 minutes

# ------------ Helpers ------------
def extract_message_text(message) -> str:
    # Prefer text, then caption; fallback if neither
    if getattr(message, "text", None):
        return message.text
    if getattr(message, "caption", None):
        return message.caption
    return "Please summarise the content of the last message."

def get_ai_response(prompt: str) -> str:
    """
    Runs in a thread via asyncio.to_thread (google.generativeai is sync).
    Handles common None/empty edge cases.
    """
    try:
        resp = model.generate_content(prompt)
        # resp.text is usually present, but guard anyway
        text = getattr(resp, "text", None)
        if text and text.strip():
            return text.strip()
        # Fallback: try candidates if text is empty
        if hasattr(resp, "candidates") and resp.candidates:
            # Try the first candidate’s text parts
            for cand in resp.candidates:
                parts = getattr(getattr(cand, "content", None), "parts", []) or []
                for p in parts:
                    t = getattr(p, "text", None)
                    if t and t.strip():
                        return t.strip()
        return "Sorry, I couldn’t generate a response right now."
    except Exception as e:
        # Optional: log e
        return "Sorry, I couldn’t generate a response right now."

async def delayed_reply(client: Client, message):
    chat_id = message.chat.id
    try:
        await asyncio.sleep(REPLY_DELAY_SECONDS)
        prompt = extract_message_text(message)
        reply_text = await asyncio.to_thread(get_ai_response, prompt)
        await message.reply_text(reply_text, quote=True, disable_web_page_preview=True)
    except asyncio.CancelledError:
        # Task was cancelled because a newer message arrived; just exit cleanly
        return
    except Exception:
        # Avoid crashing the loop on unexpected errors
        try:
            await message.reply_text("⚠️ Failed to send an AI reply.", quote=True)
        except Exception:
            pass
    finally:
        # Clean up completed task
        if pending_tasks.get(chat_id) is asyncio.current_task():
            pending_tasks.pop(chat_id, None)

# ------------ Commands ------------
# Note: set explicit prefixes in case your account uses something else
CMD_PREFIXES = ["/", "!", "."]

@app.on_message(filters.me & filters.command("away", prefixes=CMD_PREFIXES))
async def set_away(client, message):
    global is_away
    is_away = True
    await message.reply_text(
        f"✅ Status set to *Away*. I’ll auto-reply after {REPLY_DELAY_SECONDS//60} min.",
        quote=True,
    )

@app.on_message(filters.me & filters.command("back", prefixes=CMD_PREFIXES))
async def set_back(client, message):
    global is_away
    is_away = False

    # Cancel all pending delayed replies when you’re back
    for task in list(pending_tasks.values()):
        task.cancel()
    pending_tasks.clear()

    await message.reply_text("🟢 Status set to *Available*. Auto-replies disabled.", quote=True)

# ------------ Auto-reply ------------
@app.on_message(filters.private & ~filters.me)
async def handle_message(client, message):
    if not is_away:
        return  # Do nothing if available

    chat_id = message.chat.id

    # Cancel any existing scheduled reply for this chat (debounce)
    old_task = pending_tasks.get(chat_id)
    if old_task and not old_task.done():
        old_task.cancel()

    # Schedule a fresh delayed reply
    task = asyncio.create_task(delayed_reply(client, message))
    pending_tasks[chat_id] = task

# ------------ Run ------------
app.run()

