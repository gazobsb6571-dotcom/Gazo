import os, requests, telebot
from flask import Flask
from datetime import datetime
import time

app = Flask(__name__)
TOKEN = os.getenv("TELEGRAM_TOKEN")
API_KEY = os.getenv("API_KEY")
bot = telebot.TeleBot(TOKEN)

# Cache pour ne pas cramer l'API
CACHE = {"prono": {"time": 0, "data": None}, "live": {"time": 0, "data": None}}

def api_call(url):
    headers = {"x-apisports-key": API_KEY}
    try:
        r = requests.get(url, headers=headers, timeout=15).json()
        return r.get("response", [])
    except:
        return []

def analyse_confiance(fixture):
    # Score simple mais efficace
    try:
        home = fixture['teams']['home']['name']
        away = fixture['teams']['away']['name']
        league = fixture['league']['name']

        # Filtre meilleures ligues
        ligues_top = ["Premier League", "La Liga", "Ligue 1", "Bundesliga", "Serie A", "Champions League", "Europa"]
        if not any(l in league for l in ligues_top):
            return None

        # On va chercher la prédiction API
        fid = fixture['fixture']['id']
        pred = api_call(f"https://v3.football.api-sports.io/predictions?fixture={fid}")
        if not pred:
            return None

        p = pred[0]
        percent_home = int(p['predictions']['percent']['home'].replace("%",""))
        percent_away = int(p['predictions']['percent']['away'].replace("%",""))
        percent_draw = int(p['predictions']['percent']['draw'].replace("%",""))

        max_percent = max(percent_home, percent_away, percent_draw)
        if max_percent < 55: # pas assez de confiance
            return None

        if percent_home == max_percent:
            choix = f"Victoire {home}"
        elif percent_away == max_percent:
            choix = f"Victoire {away}"
        else:
            choix = "Match Nul"

        confiance = max_percent
        but_pred = p['predictions']['goals']['home'] + p['predictions']['goals']['away']
        over_under = "Over 1.5" if but_pred > 1.8 else "Under 3.5"

        return {
            "match": f"{home} vs {away}",
            "ligue": league,
            "heure": fixture['fixture']['date'][11:16],
            "choix": choix,
            "confiance": confiance,
            "conseil": over_under,
            "conseil_detail": p['predictions']['advice']
        }
    except:
        return None

@bot.message_handler(commands=['start'])
def start(m):
    bot.send_message(m.chat.id, "🏆 *GAZO V31 - ANALYSEUR PRO*\n\n/prono 🎯 - Meilleurs pronos du jour (confiance)\n/live 🔴 - Meilleurs coups LIVE\n/recap - Récap", parse_mode="Markdown")

@bot.message_handler(commands=['prono'])
def prono(m):
    try:
        now = time.time()
        # Cache 30 min
        if now - CACHE["prono"]["time"] < 1800 and CACHE["prono"]["data"]:
            bot.send_message(m.chat.id, CACHE["prono"]["data"], parse_mode="Markdown")
            return

        today = datetime.now().strftime("%Y-%m-%d")
        fixtures = api_call(f"https://v3.football.api-sports.io/fixtures?date={today}")

        if not fixtures:
            bot.send_message(m.chat.id, "⚠️ Pas de matchs aujourd'hui ou limite API atteinte. Réessaie dans 1h.")
            return

        analyses = []
        for f in fixtures[:20]: # on analyse les 20 premiers pour ne pas cramer l'API
            a = analyse_confiance(f)
            if a:
                analyses.append(a)
            time.sleep(0.3) # évite de spammer l'API

        analyses = sorted(analyses, key=lambda x: x['confiance'], reverse=True)[:5]

        if not analyses:
            txt = "📊 *GAZO V31 - PRONO DU JOUR*\n\nPas de matchs avec forte confiance aujourd'hui. Reviens demain."
        else:
            txt = f"📊 *GAZO V31 - TOP 5 PRONOS DU JOUR*\n_{today}_\n\n"
            for i, a in enumerate(analyses, 1):
                txt += f"*{i}. {a['match']}* ({a['ligue']})\n"
                txt += f"⏰ {a['heure']} | 🎯 {a['choix']} ({a['confiance']}%)\n"
                txt += f"💡 {a['conseil']} - _{a['conseil_detail']}_\n\n"

        CACHE["prono"] = {"time": now, "data": txt}
        bot.send_message(m.chat.id, txt, parse_mode="Markdown")
    except Exception as e:
        bot.send_message(m.chat.id, f"Erreur prono: {e}\nLe bot reste actif, retente /prono")

@bot.message_handler(commands=['live'])
def live(m):
    try:
        fixtures = api_call("https://v3.football.api-sports.io/fixtures?live=all")

        if not fixtures:
            bot.send_message(m.chat.id, "🔴 *LIVE*\n\nAucun match en direct pour l'instant. Reviens dans 15 min.", parse_mode="Markdown")
            return

        txt = "🔴 *GAZO V31 - MEILLEURS COUPS LIVE*\n\n"
        count = 0
        for f in fixtures[:15]:
            try:
                minute = f['fixture']['status']['elapsed']
                home = f['teams']['home']['name']
                away = f['teams']['away']['name']
                gh = f['goals']['home']
                ga = f['goals']['away']
                score = f"{gh}-{ga}"

                conseil = ""
                if minute and minute > 75 and gh == ga:
                    conseil = "💰 PARIE : Match Nul (fin de match tendue)"
                elif minute and minute > 60 and gh + ga == 0:
                    conseil = "💰 PARIE : Under 0.5 / Pas de but"
                elif gh > ga and minute and minute > 70:
                    conseil = f"💰 PARIE : Victoire {home} tient le score"
                elif ga > gh and minute and minute > 70:
                    conseil = f"💰 PARIE : Victoire {away} tient le score"
                else:
                    if abs(gh-ga) >= 2:
                        conseil = "⚠️ Éviter - match plié"
                    else:
                        conseil = "👀 Attendre 70e pour Nul ou Over"

                txt += f"*{home} vs {away}* {score} ({minute}')\n{conseil}\n\n"
                count += 1
                if count >= 5:
                    break
            except:
                continue

        if count == 0:
            txt += "Pas de bon coup live détecté pour l'instant."

        bot.send_message(m.chat.id, txt, parse_mode="Markdown")
    except Exception as e:
        # IMPORTANT : On répond toujours, même en erreur
        bot.send_message(m.chat.id, f"🔴 LIVE : Erreur temporaire ({e}), retente dans 2 min.")

@app.route('/')
def home():
    return "GAZO V31 ANALYSEUR ACTIF"

# Lancement
import threading
threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()
