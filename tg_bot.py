import os
import telebot
from telebot import types
import asyncio
import threading
import traceback
from flask import Flask, request
from dotenv import load_dotenv
from trade_engine import run_scanner
import database

load_dotenv()
BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

database.init_db()

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_start = types.KeyboardButton('▶️ Запустить торговлю')
    btn_stop = types.KeyboardButton('⏹ Остановить')
    markup.add(btn_start, btn_stop)
    bot.send_message(message.chat.id, "Привет! Я Alpha-Pulse. Управляй мной кнопками ниже.", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == '▶️ Запустить торговлю')
def start_trading(message):
    bot.send_message(message.chat.id, "Запускаю сканер рынка...")
    print(">>> ПОЛЬЗОВАТЕЛЬ НАЖАЛ КНОПКУ ЗАПУСКА. Создаю поток...")

    def run_engine():
        try:
            print(">>> ПОТОК ЗАПУЩЕН. Стартую asyncio.run(run_scanner())...")
            asyncio.run(run_scanner())
        except Exception as e:
            print(f">>> КРИТИЧЕСКАЯ ОШИБКА В ПОТОКЕ: {e}")
            traceback.print_exc() # Выведет полный стек ошибки в логи Render

    thread = threading.Thread(target=run_engine)
    thread.daemon = True
    thread.start()

@bot.message_handler(func=lambda message: message.text == '⏹ Остановить')
def stop_trading(message):
    bot.send_message(message.chat.id, "Для остановки перезагрузите сервис на Render.")

# --- ВЕБХУК ДЛЯ RENDER ---
@app.route('/' + BOT_TOKEN, methods=['POST'])
def getMessage():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

@app.route("/")
def webhook():
    bot.remove_webhook()
    bot.set_webhook(url=RENDER_URL + '/' + BOT_TOKEN)
    return "Бот запущен и слушает Telegram!", 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, threaded=True)