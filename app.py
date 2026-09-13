import os
import threading
from flask import Flask
import telebot

app = Flask(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
print(f"TOKEN present: {bool(TOKEN)}")

bot = telebot.TeleBot(TOKEN, threaded=False)

@bot.message_handler(commands=['start'])
def start(m):
    bot.reply_to(m, "GAZO VERT ! Le bot marche.")

def run_bot():
    print("Bot polling started...")
    bot.infinity_polling()

threading.Thread(target=run_bot, daemon=True).start()

@app.route('/')
def home():
    return "GAZO LIVE OK"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print(f"Starting Flask on port {port}")
    app.run(host="0.0.0.0", port=port)
