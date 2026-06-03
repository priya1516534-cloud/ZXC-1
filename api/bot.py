import os
import json
import requests
import telebot
from telebot.types import Update, InlineKeyboardMarkup, InlineKeyboardButton
from http.server import BaseHTTPRequestHandler

# Environment variables
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set")

bot = telebot.TeleBot(TOKEN)

# In‑memory state (per serverless instance). For production use a real DB.
user_states = {}  # {chat_id: {'active': bool}}

def get_keyboard():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("START 🟢", callback_data="start"),
        InlineKeyboardButton("STOP 🔴", callback_data="stop"),
        InlineKeyboardButton("UPLOAD FILE 📂", callback_data="upload")
    )
    return markup

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    chat_id = call.message.chat.id
    if call.data == "start":
        user_states[chat_id] = {'active': True}
        bot.edit_message_text(
            "✅ Automation **STARTED**. You can now upload files.",
            chat_id, call.message.message_id,
            parse_mode="Markdown", reply_markup=get_keyboard()
        )
    elif call.data == "stop":
        user_states[chat_id] = {'active': False}
        bot.edit_message_text(
            "🔴 Automation **STOPPED**. Use START to enable file processing.",
            chat_id, call.message.message_id,
            parse_mode="Markdown", reply_markup=get_keyboard()
        )
    elif call.data == "upload":
        bot.send_message(
            chat_id,
            "📂 Please send me a **.txt** or **.json** file.",
            parse_mode="Markdown"
        )

@bot.message_handler(content_types=['document'])
def handle_document(message):
    chat_id = message.chat.id
    # Check if automation is active for this user
    if not user_states.get(chat_id, {}).get('active', True):
        bot.send_message(
            chat_id,
            "⚠️ Bot is currently **STOPPED**. Press START to enable file processing.",
            parse_mode="Markdown", reply_markup=get_keyboard()
        )
        return

    file_id = message.document.file_id
    file_name = message.document.file_name

    # Real‑time status update
    bot.send_message(chat_id, f"⏳ Received `{file_name}`. Downloading...", parse_mode="Markdown")

    try:
        # Download file
        file_info = bot.get_file(file_id)
        downloaded = bot.download_file(file_info.file_path)
        content = downloaded.decode('utf-8')

        # Process based on extension
        if file_name.endswith('.json'):
            data = json.loads(content)
            result_summary = f"JSON processed. Keys: {list(data.keys())}"
        elif file_name.endswith('.txt'):
            lines = content.splitlines()
            result_summary = f"TXT processed. {len(lines)} lines, first line: {lines[0][:50]}"
        else:
            result_summary = "Unsupported file type. Please send .txt or .json."

        # Simulate automation steps
        bot.send_message(chat_id, "⚙️ Processing data...")
        # Add your real automation logic here (API calls, computations, etc.)
        # For demo, just a delay (max 10 sec, Vercel Hobby limit)
        import time
        time.sleep(2)

        bot.send_message(
            chat_id,
            f"✅ **Automation Complete**\n\n📄 File: `{file_name}`\n📊 Result: {result_summary}",
            parse_mode="Markdown", reply_markup=get_keyboard()
        )
    except Exception as e:
        bot.send_message(
            chat_id,
            f"❌ Error: {str(e)}\nPlease try again.",
            reply_markup=get_keyboard()
        )

@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    user_states[chat_id] = {'active': True}
    bot.send_message(
        chat_id,
        "🤖 *Automation Bot*\n\nUse the buttons below to control me.\n- START: enable file processing\n- STOP: disable\n- UPLOAD FILE: send a .txt or .json",
        parse_mode="Markdown",
        reply_markup=get_keyboard()
    )

# Vercel serverless handler
class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        update_dict = json.loads(post_data.decode('utf-8'))
        update = Update.de_json(update_dict)
        bot.process_new_updates([update])
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(b'{"ok": true}')

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Telegram bot webhook is running.')
