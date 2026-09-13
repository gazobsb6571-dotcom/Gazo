import os
import json
import time
import threading
import requests
from datetime import datetime
from flask import Flask
import telebot

app = Flask(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
API_KEY = os.getenv("API_KEY")
API_HOST = "v3.football.api-sports.io"
STATS_FILE = "stats.json"

print(f"TOKEN: {bool(TOKEN)} | API_KEY: {bool(API_KEY)}")

bot = None
if TOKEN:
    bot = telebot.TeleBot(TOKEN, threaded=False)

cache = {"pronos": None, "time": 0}

def load_stats():
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Erreur lecture stats: {e}")
    return {"gagnes": 0, "perdus": 0, "benef": 0.0}

def save_stats():
    try:
        with open(STATS_FILE, "w") as f:
            json.dump(stats, f)
    except Exception as e:
        print(f"Erreur sauvegarde stats: {e}")

stats = load_stats()

def get_pronos():
    if time.time() - cache["time"] < 1800 and cache["pronos"]:
        return cache["pronos"]
    if not API_KEY:
        return "⚠️ API_KEY manquant."
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        headers = {"x-apisports-key": API_KEY}
        r = requests.get(f"https://{API_HOST}/predictions?date={today}", headers=headers, timeout=15)
        r.raise_for_status()
        data = r.json()
        resp = data.get("response", [])
        if not resp:
            return f"📭 Pas de prédictions pour {today} (API vide)."
        msg = f"🏆 **GAZO V31.3 - TOP 5 PRONOS {today}**\n\n"
        for i, item in enumerate(resp[:5]):
            try:
                teams = item["teams"]
                pred = item["predictions"]
                league = item["league"]["name"]
                msg += f"{i+1}. [{league}] {teams['home']['name']} vs {teams['away']['name']}\n"
                msg += f" 👉 {pred.get('advice', 'N/A')} ({pred.get('winning_percent', '?')})\n\n"
            except (KeyError, TypeError):
                continue
        cache["pronos"] = msg
        cache["time"] = time.time()
        return msg
    except requests.exceptions.RequestException as e:
        print(f"API ERROR: {e}")
        return "⚠️ Erreur de connexion à l'API. Réessaie dans quelques minutes."
    except Exception as e:
        print(f"API ERROR: {e}")
        return "⚠️ Une erreur inattendue est survenue."

HELP_TEXT = (
    "🏆 **GAZO V31.3 - LIVE VERT**\n\n"
    "Commandes dispo:\n"
    "/prono 🎯 - Top pronos du jour\n"
    "/live 🔴 - Matchs 70'+\n"
    "/bilan 💰 - Ton bilan\n"
    "/win <montant> ✅ - Enregistrer un pari gagné\n"
    "/lose <montant> ❌ - Enregistrer un pari perdu\n"
    "/recap 📊 - Résumé complet\n"
    "/help ❓ - Cette aide"
)

if bot:
    @bot.message_handler(commands=['start', 'help'])
    def cmd_start(m):
        bot.reply_to(m, HELP_TEXT, parse_mode="Markdown")

    @bot.message_handler(commands=['prono'])
    def cmd_prono(m):
        bot.send_message(m.chat.id, "⏳ Analyse GAZO en cours...")
        txt = get_pronos()
        bot.send_message(m.chat.id, txt, parse_mode="Markdown")

    @bot.message_handler(commands=['live'])
    def cmd_live(m):
        if not API_KEY:
            bot.reply_to(m, "⚠️ API_KEY manquant.")
            return
        try:
            headers = {"x-apisports-key": API_KEY}
            r = requests.get(f"https://{API_HOST}/fixtures?live=all", headers=headers, timeout=15)
            r.raise_for_status()
            live = r.json().get("response", [])
            if not live:
                bot.reply_to(m, "🔴 Aucun match live actuellement.")
                return
            msg = "🔴 **LIVE 70'+ - OPPORTUNITÉS**\n\n"
            count = 0
            for g in live:
                try:
                    el = g["fixture"]["status"]["elapsed"] or 0
                    if el >= 70:
                        home = g["teams"]["home"]["name"]
                        away = g["teams"]["away"]["name"]
                        gh = g["goals"]["home"]
                        ga = g["goals"]["away"]
                        msg += f"⚽ {home} {gh}-{ga} {away} ({el}')\n"
                        if gh == ga:
                            msg += " 💡 Pari: +0.5 But ou Nul safe\n"
                        elif abs(gh - ga) == 1:
                            msg += " 💡 Pari: Double Chance\n"
                        msg += "\n"
                        count += 1
                except (KeyError, TypeError):
                    continue
            if count == 0:
                msg += "Pas de match >=70' pour l'instant. Revient dans 10 min."
            bot.send_message(m.chat.id, msg, parse_mode="Markdown")
        except requests.exceptions.RequestException as e:
            print(f"LIVE ERROR: {e}")
            bot.reply_to(m, "⚠️ Erreur de connexion à l'API live.")

    @bot.message_handler(commands=['bilan'])
    def cmd_bilan(m):
        total = stats["gagnes"] + stats["perdus"]
        roi = (stats["benef"] / total * 100) if total > 0 else 0
        msg = (
            f"💰 **BILAN GAZO**\n\n"
            f"Gagnés: {stats['gagnes']}\n"
            f"Perdus: {stats['perdus']}\n"
            f"Total: {total}\n"
            f"Bénéf: {stats['benef']:.2f}€\n"
            f"ROI: {roi:.1f}%"
        )
        bot.reply_to(m, msg, parse_mode="Markdown")

    def _parse_amount(m):
        parts = m.text.split()
        if len(parts) < 2:
            return None
        try:
            return float(parts[1].replace(",", "."))
        except ValueError:
            return None

    @bot.message_handler(commands=['win'])
    def cmd_win(m):
        amount = _parse_amount(m)
        if amount is None:
            bot.reply_to(m, "Usage: /win <montant> (ex: /win 15.50)")
            return
        stats["gagnes"] += 1
        stats["benef"] += amount
        save_stats()
        bot.reply_to(m, f"✅ Pari gagné enregistré (+{amount:.2f}€). Nouveau bénéf: {stats['benef']:.2f}€")

    @bot.message_handler(commands=['lose'])
    def cmd_lose(m):
        amount = _parse_amount(m)
        if amount is None:
            bot.reply_to(m, "Usage: /lose <montant> (ex: /lose 10)")
            return
        stats["perdus"] += 1
        stats["benef"] -= amount
        save_stats()
        bot.reply_to(m, f"❌ Pari perdu enregistré (-{amount:.2f}€). Nouveau bénéf: {stats['benef']:.2f}€")

    @bot.message_handler(commands=['recap'])
    def cmd_recap(m):
        total = stats["gagnes"] + stats["perdus"]
        roi = (stats["benef"] / total * 100) if total > 0 else 0
        bilan = (
            f"💰 Bilan: {stats['gagnes']}G / {stats['perdus']}P "
            f"| Bénéf: {stats['benef']:.2f}€ | ROI: {roi:.1f}%\n\n"
        )
        bot.send_message(m.chat.id, bilan + get_pronos(), parse_mode="Markdown")

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
    return "GAZO V31.3 LIVE OK - PRONO + LIVE + BILAN + WIN/LOSE"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print(f"Starting Flask on port {port}")
    app.run(host="0.0.0.0", port=port)
