import os
import telebot
from telebot import apihelper
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
ADMIN_ID = os.getenv("TG_ADMIN_ID")

# УКАЖИ ЗДЕСЬ ПОРТ ТВОЕГО VPN, ЕСЛИ ОН ЕСТЬ!
# apihelper.proxy = {'https': 'socks5://127.0.0.1:1080'}

bot = telebot.TeleBot(BOT_TOKEN) if BOT_TOKEN else None

async def send_msg(text):
    """Отправляет сообщение в Telegram."""
    if not bot: return
    try:
        bot.send_message(ADMIN_ID, text, parse_mode='Markdown')
    except Exception as e:
        print(f"TG Error: {e}")