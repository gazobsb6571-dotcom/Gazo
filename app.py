import os, requests, telebot, threading
from flask import Flask
app = Flask(__name__)
TOKEN = os.getenv("TELEGRAM_TOKEN")
API_KEY = os.getenv("API_KEY")
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start','prono'])
def prono(message):
    try:
        url = "https://v3.football.api-sports.io/fixtures?date=2026-09-14"
        h = {"x-apisports-key": API_KEY}
        data = requests.get(url, headers=h, timeout=15).json()
        txt = "🏆 *GAZO V30 - BETCLIC*\n\n"
        for m in data.get('response', [])[:6]:
            home = m['teams']['home']['name']
            away = m['teams']['away']['name']
            txt += f"⚽ {home} vs {away}\n👉 1X + Over 1.5\n\n"
        if not data.get('response'):
            txt += "Pas de matchs aujourd'hui Gazo !"
        bot.send_message(message.chat.id, txt, parse_mode="Markdown")
    except Exception as e:
        bot.send_message(message.chat.id, f"Erreur: {e}")

@app.route('/')
def home():
    return "GAZO V30 ACTIF"

threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()
