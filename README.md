Telegram AI Userbot

A Telegram userbot built with Pyrogram
 and Google Gemini
 that auto-replies to private messages in real time.
It supports instant replies, per-chat history, and runs 24/7 on a server.

✨ Features

🤖 Auto-replies to private chats when set /away

🧠 Keeps last 15 messages of history per chat for contextual replies

⚡ Instant responses (no delay)

🔒 Runs as a userbot (your account, not a bot token)

🐧 Works on Linux (tested on Oracle Cloud VM, Ubuntu 22.04)

🔧 Systemd service included for always-on deployment

📦 Requirements

Python 3.11+

A Telegram API ID & API Hash

A Gemini API Key

Virtual environment recommended

⚙️ Installation
# clone the repo
git clone https://github.com/Abhisharma08/auto.git
cd auto

# create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# install dependencies
pip install -U pip
pip install -r requirements.txt

🔑 Configuration

Create a .env file (⚠️ keep it private, never commit to git):

API_ID=
API_HASH=
GEMINI_API_KEY=your_google_gemini_api_key
GEMINI_MODEL=gemini-2.0-flash
SESSION_DIR=/opt/app/data
MAX_HISTORY=15

▶️ Running
1. First-time login
source .venv/bin/activate
python auto.py


Enter your Telegram phone number, login code, and (if enabled) 2FA password.
A session file will be created under /opt/app/data.

2. Run permanently with systemd

Create a service file:

[Unit]
Description=Telegram Pyrogram Userbot
After=network-online.target

[Service]
User=ubuntu
WorkingDirectory=/opt/app/code
Environment=PYTHONUNBUFFERED=1
EnvironmentFile=/opt/app/code/.env
ExecStart=/opt/app/code/.venv/bin/python /opt/app/code/auto.py
Restart=always
RestartSec=5
StandardOutput=append:/opt/app/logs/out.log
StandardError=append:/opt/app/logs/err.log

[Install]
WantedBy=multi-user.target


Enable & start:

sudo systemctl daemon-reload
sudo systemctl enable tg-userbot
sudo systemctl start tg-userbot

💬 Commands

/away → Enable auto-replies

/back → Disable auto-replies

/status → Show current status

/clear → Clear chat history memory for current chat

📂 Project Structure
auto/
├── auto.py          # main bot script
├── requirements.txt # dependencies
├── README.md        # project docs
└── .gitignore       # excludes .env, venv, sessions

🛡️ Security Notes

Don’t share your .env (API keys + session file).

Always regenerate keys if they were ever exposed.

Use a dedicated API_ID/API_HASH for this bot.

📝 License

This project is open-source under the MIT License
.
