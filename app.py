import os
import time
import threading
import requests
from flask import Flask
import telebot

app = Flask(__name__)

# --- CONFIG ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
API_KEY = os.getenv("API_KEY")
API_HOST = "v3.football.api-sports.io"

print(f"START CHECK -> TOKEN: {bool(TELEGRAM_TOKEN)} | API_KEY: {bool(API_KEY)}")

bot = None
if TELEGRAM_TOKEN:
    bot = telebot.TeleBot(TELEGRAM_TOKEN, threaded=False)

    # --- CACHE SIMPLE POUR NE PAS CRAMER L'API ---
    cache = {"pronos": None, "time": 0}

    def get_predictions():
        # 30 min cache
        if time.time() - cache["time"] < 1800 and cache["pronos"]:
            return cache["pronos"]
        if not API_KEY:
            return "⚠️ API_KEY manquant sur Render."
        try:
            # On prend les matchs du jour
            from datetime import datetime
            today = datetime.now().strftime("%Y-%m-%d")
            headers = {"x-apisports-key": API_KEY}
            url = f"https://{API_HOST}/predictions?date={today}"
            r = requests.get(url, headers=headers, timeout=15)
            data = r.json()
            if not data.get("response"):
                return "Pas de pronos disponibles aujourd'hui (API vide)."
            
            msg = "🏆 **GAZO V31.2 - TOP 5 PRONOS DU JOUR**\n\n"
            for i, item in enumerate(data["response"][:5]):
                fixture = item["fixture"]
                teams = item["teams"]
                pred = item["predictions"]
                msg += f"{i+1}. {teams['home']['name']} vs {teams['away']['name']}\n"
                msg += f"   -> Conseil: {pred.get('advice','N/A')} | Confiance: {pred.get('winning_percent','?')}\n\n"
            
            cache["pronos"] = msg
            cache["time"] = time.time()
            return msg
        except Exception as e:
            print(f"API ERROR: {e}")
            return f"Erreur API: {e}"

    @bot.message_handler(commands=['start'])
    def cmd_start(m):
        bot.reply_to(m, "🏆 **GAZO V31.2 LIVE !**\nBot opérationnel.\n\nCommandes:\n/prono - Top pronos du jour\n/live - Matchs en cours (75e)")

    @bot.message_handler(commands=['prono'])
    def cmd_prono(m):
        bot.reply_to(m, "⏳ Analyse en cours...")
        txt = get_predictions()
        bot.send_message(m.chat.id, txt, parse_mode="Markdown")

    @bot.message_handler(commands=['live'])
    def cmd_live(m):
        if not API_KEY:
            bot.reply_to(m, "API_KEY manquant")
            return
        try:
            headers = {"x-apisports-key": API_KEY}
            url = f"https://{API_HOST}/fixtures?live=all"
            r = requests.get(url, headers=headers, timeout=15)
            data = r.json()
            live_games = data.get("response", [])
            if not live_games:
                bot.reply_to(m, "Aucun match live pour le moment.")
                return
            
            msg = "🔴 **LIVE EN COURS**\n\n"
            found = 0
            for game in live_games:
                minute = game["fixture"]["status"]["elapsed"] or 0
                if minute >= 70:
                    home = game["teams"]["home"]["name"]
                    away = game["teams"]["away"]["name"]
                    score_h = game["goals"]["home"]
                    score_a = game["goals"]["away"]
                    msg += f"⚽ {home} {score_h}-{score_a} {away} ({minute}')\n"
                    if score_h == score_a:
                        msg += "   -> Opportunité: Nul ou Under se dessine\n"
                    found += 1
            if found == 0:
                msg += "Pas de match >=70' intéressant actuellement."
            bot.reply_to(m, msg, parse_mode="Markdown")
        except Exception as e:
            bot.reply_to(m, f"Erreur live: {e}")

    def run_bot():
        print("Bot polling started...")
        while True:
            try:
                bot.infinity_polling(timeout=60, long_polling_timeout=60)
            except Exception as e:
                print(f"Polling crash: {e}")
                time.sleep(5)

    threading.Thread(target=run_bot, daemon=True).start()

@app.route('/')
def home():
    return "GAZO V31.2 LIVE OK - 2026"
