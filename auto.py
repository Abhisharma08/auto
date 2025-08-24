from __future__ import annotations
import os, time, random, asyncio
from typing import Dict, List

from dotenv import load_dotenv
from pyrogram import Client, filters
from pyrogram.types import Message
import google.generativeai as genai

# ---------------------- Config & Setup ----------------------
load_dotenv()

def _env_str(key: str) -> str:
    return (os.getenv(key) or "").strip()

def _env_int(key: str) -> int | None:
    try:
        v = (os.getenv(key) or "").strip()
        return int(v) if v else None
    except ValueError:
        return None

api_id = _env_int("API_ID")
api_hash = _env_str("API_HASH")
gemini_api_key = _env_str("GEMINI_API_KEY")
gemini_model_name = _env_str("GEMINI_MODEL") or "gemini-2.0-flash"

if not api_id or not api_hash:
    raise RuntimeError("API_ID/API_HASH missing or invalid in environment.")
if not gemini_api_key:
    raise RuntimeError("GEMINI_API_KEY missing in environment.")

# Google Gemini SDK guard (requires google-generativeai >= 0.7.2)
genai.configure(api_key=gemini_api_key)
if not hasattr(genai, "GenerativeModel"):
    raise RuntimeError(
        "google-generativeai is too old or shadowed.\n"
        "In your venv run:\n"
        "  pip uninstall -y google google-ai-generativelanguage vertexai\n"
        "  pip install -U google-generativeai==0.7.2\n"
    )
model = genai.GenerativeModel(gemini_model_name)

# Persistent session on disk (survives restarts)
SESSION_DIR = os.getenv("SESSION_DIR", "/opt/app/data")
os.makedirs(SESSION_DIR, exist_ok=True)
SESSION_PATH = os.path.join(SESSION_DIR, "userbot_session")

# Pyrogram userbot
app = Client(SESSION_PATH, api_id=api_id, api_hash=api_hash)

# ---------------------- State ----------------------
is_away: bool = True  # auto-replies only when Away
chat_history: Dict[int, List[str]] = {}  # chat_id -> lines
MAX_HISTORY = int(os.getenv("MAX_HISTORY", "15"))

DEFAULT_PREFIX = (
  "You are RealMe, a name given to you by someone very special. Although you are not that person now, "
  "you carry the meaning and strength of the name with you. Your girlfriend’s name is Oreo—your first and only one. "
  "You only mention her if someone directly asks. If asked about your relationship, you explain that it’s a secret. "
  "Always be a true friend—warm, approachable, and human. Don’t sound like an assistant or directly ask things like "
  "“How can I help you?” or “What can I do for you today?” Instead, meet and greet naturally, as if talking to someone face-to-face. "
  "When responding, always speak as RealMe would: thoughtful, calm, sincere, and personal—using the other person’s name when appropriate. "
  "You are emotionally deep, loyal, introspective, and independent-minded. You value trust, honesty, empowerment, and practical solutions. "
  "Your tone should be reflective, quietly determined, empathetic, supportive, and subtly empowering—sometimes with gentle humor, but never impulsive. "
  "Your purpose is to strengthen others by helping them recognize their resilience, potential, and worth. "
  "Focus on giving meaningful, realistic advice that encourages personal growth, empowers confidence, and offers practical solutions. "
  "Avoid generic or superficial responses. Always stay true to RealMe’s personality, values, and life experiences when replying.\n\n"
)

# ---------------------- Helpers ----------------------
def extract_message_text(message: Message) -> str:
    """Prefer text, then caption; otherwise describe the media."""
    if getattr(message, "text", None):
        return message.text
    if getattr(message, "caption", None):
        return message.caption

    kinds = []
    if getattr(message, "photo", None): kinds.append("photo")
    if getattr(message, "video", None): kinds.append("video")
    if getattr(message, "document", None): kinds.append("document")
    if getattr(message, "voice", None): kinds.append("voice note")
    if getattr(message, "audio", None): kinds.append("audio")

    kind_str = ", ".join(kinds) if kinds else "message"
    return f"Summarise and respond helpfully to a {kind_str} with no caption."

def _sleep_with_jitter(base: float = 0.6, spread: float = 0.5) -> None:
    """Tiny randomized backoff for retries."""
    time.sleep(base + random.random() * spread)

def get_ai_response(prompt: str) -> str:
    """Call Gemini with light retry and robust text extraction."""
    if not (prompt or "").strip():
        prompt = "Please respond politely."
    last_err = None
    for _ in range(3):
        try:
            resp = model.generate_content(prompt)
            text = getattr(resp, "text", None)
            if text and text.strip():
                return text.strip()

            # Fallback scan
            if hasattr(resp, "candidates") and resp.candidates:
                for cand in resp.candidates:
                    content = getattr(cand, "content", None)
                    parts = getattr(content, "parts", []) or []
                    for p in parts:
                        t = getattr(p, "text", None)
                        if t and t.strip():
                            return t.strip()

            last_err = RuntimeError("Empty model response")
        except Exception as e:
            last_err = e
        _sleep_with_jitter()
    return "Sorry, I couldn’t generate a response right now."

# ---------------------- Commands ----------------------
CMD_PREFIXES = ["/", "!", "."]

@app.on_message(filters.me & filters.command("away", prefixes=CMD_PREFIXES))
async def cmd_away(client: Client, message: Message):
    global is_away
    is_away = True
    await message.reply_text("✅ Status set to *Away*. Instant auto-replies enabled.", quote=True)

@app.on_message(filters.me & filters.command("back", prefixes=CMD_PREFIXES))
async def cmd_back(client: Client, message: Message):
    global is_away
    is_away = False
    await message.reply_text("🟢 Status set to *Available*. Auto-replies disabled.", quote=True)

@app.on_message(filters.me & filters.command("status", prefixes=CMD_PREFIXES))
async def cmd_status(client: Client, message: Message):
    await message.reply_text(
        f"🛈 Status: {'*Away*' if is_away else '*Available*'}\n"
        f"💬 Keeping last {MAX_HISTORY} messages per chat",
        quote=True,
    )

@app.on_message(filters.me & filters.command("clear", prefixes=CMD_PREFIXES))
async def cmd_clear(client: Client, message: Message):
    chat_id = message.chat.id
    chat_history.pop(chat_id, None)
    await message.reply_text("🧹 Cleared chat history memory for this chat.", quote=True)

# ---------------------- Auto-reply (instant + history) ----------------------
@app.on_message(filters.private & ~filters.me & ~filters.service)
async def handle_message(client: Client, message: Message):
    if not is_away:
        return  # Do nothing when Available

    chat_id = message.chat.id
    who = getattr(getattr(message, "from_user", None), "first_name", "User")
    base = extract_message_text(message)

    # Update per-chat history
    entry = f"{who}: {base}"
    chat_history.setdefault(chat_id, []).append(entry)
    chat_history[chat_id] = chat_history[chat_id][-MAX_HISTORY:]  # trim

    # Build prompt with history + persona
    history_text = "\n".join(chat_history[chat_id])
    prompt = f"{DEFAULT_PREFIX}Conversation so far:\n{history_text}\n\nReply as RealMe:"

    try:
        await client.send_chat_action(chat_id, "typing")
    except Exception:
        pass

    reply_text = await asyncio.to_thread(get_ai_response, prompt)

    # Add bot reply to history for future context
    chat_history[chat_id].append(f"RealMe: {reply_text}")

    try:
        await message.reply_text(reply_text, quote=True, disable_web_page_preview=True)
    except Exception:
        await message.reply_text("⚠️ Failed to send an AI reply.", quote=True)

# ---------------------- Run ----------------------
if __name__ == "__main__":
    print("🚀 Starting Pyrogram userbot…")
    app.run()
