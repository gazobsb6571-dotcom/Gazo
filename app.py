import os
import threading
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import requests
from datetime import datetime

app = Flask(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY")

print(f"DEBUG: TELEGRAM_TOKEN present? {bool(TELEGRAM_TOKEN)} len={len(TELEGRAM_TOKEN) if TELEGRAM_TOKEN else 0}", flush=True)
print(f"DEBUG: API_FOOTBALL_KEY present? {bool(API_FOOTBALL_KEY)}", flush=True)

@app.route('/')
def home():
    return "GAZO BOT IS LIVE - OK"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔥 GAZO est en ligne ! Tape /live pour voir les matchs")

async def live(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not API_FOOTBALL_KEY:
        await update.message.reply_text("API_FOOTBALL_KEY manquante")
        return
    try:
        url = "https://v3.football.api-sports.io/fixtures?live=all"
        headers = {"x-apisports-key": API_FOOTBALL_KEY}
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json()
        live_matches = data.get("response", [])
        if not live_matches:
            await update.message.reply_text("Aucun match live maintenant 🕒")
            return
        msg = "🔴 LIVE NOW:\n\n"
        for m in live_matches[:10]:
            home = m['teams']['home']['name']
            away = m['teams']['away']['name']
            gh = m['goals']['home']
            ga = m['goals']['away']
            minute = m['fixture']['status']['elapsed']
            msg += f"{home} {gh}-{ga} {away} ({minute}')\n"
        await update.message.reply_text(msg)
    except Exception as e:
        await update.message.reply_text(f"Erreur: {e}")

async def statut(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"✅ Bot OK\nHeure: {datetime.now()}")

def run_bot():
    print(">>> Tentative lancement bot...", flush=True)
    if not TELEGRAM_TOKEN:
        print("❌ ERREUR FATALE: TELEGRAM_TOKEN manquant", flush=True)
        return
    try:
        application = Application.builder().token(TELEGRAM_TOKEN).build()
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("live", live))
        application.add_handler(CommandHandler("statut", statut))
        print("🤖 GAZO démarré - polling...", flush=True)
        application.run_polling()
    except Exception as e:
        print(f"❌ ERREUR BOT: {e}", flush=True)

# Lancement du bot dans un thread
threading.Thread(target=run_bot, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
