import os
import telebot
from telebot import types
import asyncio
import threading
from flask import Flask, request
from dotenv import load_dotenv
from trade_engine import run_scanner
import notifier

load_dotenv()
BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL") # Render сам даст эту ссылку

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# Храним задачу, чтобы можно было остановить
scanner_task = None
loop = None

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_start = types.KeyboardButton('▶️ Запустить торговлю')
    btn_stop = types.KeyboardButton('⏹ Остановить')
    markup.add(btn_start, btn_stop)
    bot.send_message(message.chat.id, "Привет! Я Alpha-Pulse. Управляй мной кнопками ниже.", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == '▶️ Запустить торговлю')
def start_trading(message):
    global scanner_task
    if scanner_task and not scanner_task.done():
        bot.send_message(message.chat.id, "Бот уже работает!")
        return

    bot.send_message(message.chat.id, "Запускаю сканер рынка...")
    # Запускаем асинхронный движок в фоновом потоке
    scanner_task = asyncio.run_coroutine_threadsafe(run_scanner(), loop)

@bot.message_handler(func=lambda message: message.text == '⏹ Остановить')
def stop_trading(message):
    global scanner_task
    if scanner_task and not scanner_task.done():
        scanner_task.cancel()
        bot.send_message(message.chat.id, "Торговля остановлена.")
    else:
        bot.send_message(message.chat.id, "Бот и так не работает.")

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
    # Устанавливаем вебхук на адрес, который даст Render
    bot.set_webhook(url=RENDER_URL + '/' + BOT_TOKEN)
    return "Бот запущен и слушает Telegram!", 200

# Запуск асинхронного цикла в фоне
def start_async_loop():
    global loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_forever()

if __name__ == '__main__':
    # Запускаем асинхронный цикл для торгового движка
    threading.Thread(target=start_async_loop, daemon=True).start()

    # Запускаем Flask-сервер для Render
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)