import os, requests, telebot, threading, time
from flask import Flask
from datetime import datetime

app = Flask(__name__)
TOKEN = os.getenv("TELEGRAM_TOKEN")
API_KEY = os.getenv("API_KEY")
bot = telebot.TeleBot(TOKEN, threaded=False)

CACHE = {"prono": {"time": 0, "data": None}}

def api_call(url):
    headers = {"x-apisports-key": API_KEY}
    try:
        r = requests.get(url, headers=headers, timeout=15).json()
        return r.get("response", [])
    except:
        return []

@bot.message_handler(commands=['start'])
def start(m):
    bot.send_message(m.chat.id, "🏆 *GAZO V31 PRO ACTIF*\n\n/prono 🎯 - Top 5 matchs du jour avec confiance\n/live 🔴 - Meilleurs coups LIVE", parse_mode="Markdown")

@bot.message_handler(commands=['prono'])
def prono(m):
    try:
        now = time.time()
        if now - CACHE["prono"]["time"] < 1800 and CACHE["prono"]["data"]:
            bot.send_message(m.chat.id, CACHE["prono"]["data"], parse_mode="Markdown")
            return

        today = datetime.now().strftime("%Y-%m-%d")
        fixtures = api_call(f"https://v3.football.api-sports.io/fixtures?date={today}")

        if not fixtures:
            bot.send_message(m.chat.id, "📊 Pas de matchs ou limite API. Réessaie dans 30 min.")
            return

        txt = f"📊 *TOP 5 PRONOS DU JOUR - {today}*\n\n"
        count = 0
        for f in fixtures[:25]:
            try:
                fid = f['fixture']['id']
                home = f['teams']['home']['name']
                away = f['teams']['away']['name']
                heure = f['fixture']['date'][11:16]
                ligue = f['league']['name']

                pred = api_call(f"https://v3.football.api-sports.io/predictions?fixture={fid}")
                if not pred: continue
                p = pred[0]
                pct_home = int(p['predictions']['percent']['home'].replace("%",""))
                pct_away = int(p['predictions']['percent']['away'].replace("%",""))
                pct_draw = int(p['predictions']['percent']['draw'].replace("%",""))
                best = max(pct_home, pct_away, pct_draw)
                if best < 60: continue

                if best == pct_home: choix = f"Victoire {home}"
                elif best == pct_away: choix = f"Victoire {away}"
                else: choix = "Nul"

                conseil = p['predictions']['advice']
                txt += f"*{count+1}. {home} vs {away}* ({heure})\n{ligue}\n🎯 {choix} - Confiance {best}%\n💡 {conseil}\n\n"
                count += 1
                if count >= 5: break
                time.sleep(0.4)
            except:
                continue

        if count == 0:
            txt += "Pas de matchs à haute confiance aujourd'hui."

        CACHE["prono"]["time"] = now
        CACHE["prono"]["data"] = txt
        bot.send_message(m.chat.id, txt, parse_mode="Markdown")
    except Exception as e:
        bot.send_message(m.chat.id, f"Erreur /prono: {e}")

@bot.message_handler(commands=['live'])
def live(m):
    try:
        fixtures = api_call("https://v3.football.api-sports.io/fixtures?live=all")
        if not fixtures:
            bot.send_message(m.chat.id, "🔴 *LIVE*\n\nAucun match live maintenant.", parse_mode="Markdown")
            return

        txt = "🔴 *MEILLEURS COUPS LIVE*\n\n"
        c = 0
        for f in fixtures[:15]:
            try:
                minute = f['fixture']['status']['elapsed'] or 0
                home = f['teams']['home']['name']
                away = f['teams']['away']['name']
                gh = f['goals']['home']
                ga = f['goals']['away']

                if minute >= 75 and gh == ga:
                    conseil = "💰 PARIE : MATCH NUL"
                elif minute >= 70 and gh+ga == 0:
                    conseil = "💰 PARIE : 0 BUT - UNDER"
                elif gh > ga and minute >= 70:
                    conseil = f"💰 {home} VA GAGNER"
                elif ga > gh and minute >= 70:
                    conseil = f"💰 {away} VA GAGNER"
                else:
                    conseil = "👀 Attendre 75e minute"

                txt += f"*{home} {gh}-{ga} {away}* ({minute}')\n{conseil}\n\n"
                c += 1
                if c >= 5: break
            except:
                continue

        bot.send_message(m.chat.id, txt, parse_mode="Markdown")
    except Exception as e:
        bot.send_message(m.chat.id, f"🔴 LIVE - Erreur: {e}. Réessaie.")

@app.route('/')
def home():
    return "GAZO V31.1 ACTIF"

def run_bot():
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except:
            time.sleep(5)

threading.Thread(target=run_bot, daemon=True).start()
