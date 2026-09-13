import os, requests, telebot, threading
from flask import Flask

app = Flask(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
API_KEY = os.getenv("API_KEY")
print(f"TOKEN present: {bool(TOKEN)}")

bot = None
if TOKEN:
    bot = telebot.TeleBot(TOKEN, threaded=False)

    @bot.message_handler(commands=['start'])
    def start(m):
        bot.reply_to(m, "🏆 GAZO V31.1 LIVE ! Bot opérationnel.\n/prono /live")

    @bot.message_handler(commands=['prono','live'])
    def handle(m):
        bot.reply_to(m, "Reçu ! Version complète arrive après ce deploy vert.")

    def run_bot():
        print("Bot polling started")
        while True:
            try:
                bot.infinity_polling(timeout=60)
            except Exception as e:
                print(f"Polling error: {e}")

    threading.Thread(target=run_bot, daemon=True).start()
else:
    print("TELEGRAM_TOKEN manquant !")

@app.route('/')
def home():
    return "GAZO LIVE - OK"

# Render a besoin de cette ligne pour gunicorn
# Ne mets PAS de app.run()
