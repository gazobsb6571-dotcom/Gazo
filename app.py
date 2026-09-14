import os
import threading
import requests
from datetime import date
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY")
API_URL = "https://v3.football.api-sports.io"
MAX_LANCEMENTS_PAR_JOUR = 9

# Petit serveur web pour Render
web_app = Flask(__name__)
@web_app.route('/')
def home(): return "GAZO BOT LIVE - OK"

lancements_du_jour = 0
date_compteur = date.today()

def verifier_limite():
    global lancements_du_jour, date_compteur
    aujourd_hui = date.today()
    if aujourd_hui!= date_compteur:
        date_compteur = aujourd_hui
        lancements_du_jour = 0
    if lancements_du_jour >= MAX_LANCEMENTS_PAR_JOUR: return False
    lancements_du_jour += 1
    return True

def appel_api(endpoint, params=None):
    headers = {"x-apisports-key": API_FOOTBALL_KEY}
    try:
        r = requests.get(API_URL + endpoint, headers=headers, params=params, timeout=15)
        if r.status_code!=200: return None
        return r.json().get("response", [])
    except: return None

def valeur_statistique(stats, nom):
    for s in stats:
        if s.get("type")==nom:
            v = s.get("value")
            if v is None: return 0
            if isinstance(v,str): v=v.replace("%","")
            try: return float(v)
            except: return 0
    return 0

def obtenir_statistiques(fid):
    res = appel_api("/fixtures/statistics", {"fixture": fid})
    if not res or len(res)<2: return None
    return {
        "possession_dom": valeur_statistique(res[0].get("statistics",[]),"Ball Possession"),
        "possession_ext": valeur_statistique(res[1].get("statistics",[]),"Ball Possession"),
        "tirs_cadres_dom": valeur_statistique(res[0].get("statistics",[]),"Shots on Goal"),
        "tirs_cadres_ext": valeur_statistique(res[1].get("statistics",[]),"Shots on Goal"),
        "attaques_dangereuses_dom": valeur_statistique(res[0].get("statistics",[]),"Dangerous Attacks"),
        "attaques_dangereuses_ext": valeur_statistique(res[1].get("statistics",[]),"Dangerous Attacks"),
        "corners_dom": valeur_statistique(res[0].get("statistics",[]),"Corner Kicks"),
        "corners_ext": valeur_statistique(res[1].get("statistics",[]),"Corner Kicks"),
        "cartons_rouges_dom": valeur_statistique(res[0].get("statistics",[]),"Red Cards"),
        "cartons_rouges_ext": valeur_statistique(res[1].get("statistics",[]),"Red Cards"),
    }

def pronostic_buts(total_buts, tirs, attaques):
    lignes=[1.5,2.5,3.5,4.5]; res=[]
    for l in lignes:
        if total_buts>l: c="OVER déjà validé"
        elif tirs>=6 and attaques>=100: c="OVER possible"
        elif tirs<=2 and attaques<70: c="UNDER plus prudent"
        else: c="Incertain"
        res.append(f"{l} : {c}")
    return "\n".join(res)

def analyser_match(m):
    f=m["fixture"]; e=m["teams"]; b=m["goals"]
    minute=f["status"].get("elapsed") or 0
    dom=e["home"]["name"]; ext=e["away"]["name"]
    bd=b.get("home") or 0; be=b.get("away") or 0; tot=bd+be
    stats=obtenir_statistiques(f["id"])
    if not stats: return None
    if stats["cartons_rouges_dom"]>0 or stats["cartons_rouges_ext"]>0: return None
    pd, pe = stats["possession_dom"], stats["possession_ext"]
    td, te = stats["tirs_cadres_dom"], stats["tirs_cadres_ext"]
    ad, ae = stats["attaques_dangereuses_dom"], stats["attaques_dangereuses_ext"]
    press_dom=pd+ad+td*6; press_ext=pe+ae+te*6
    pari=""; alerte=""
    if bd==be:
        if press_dom>press_ext+35 and pd>58: pari=f"🔥 VICTOIRE IMMINENTE : {dom} (1)"
        elif press_ext>press_dom+35 and pe>58: pari=f"🔥 VICTOIRE IMMINENTE : {ext} (2)"
        else:
            pari="🤝 NUL IMMINENT (X)"
            if tot>=2: alerte=f"⚠️ ALERTE MOINS DE BUTS : Under {tot+0.5}"
    elif abs(bd-be)==1:
        lead=dom if bd>be else ext
        if (press_dom>press_ext+20 and bd>be) or (press_ext>press_dom+20 and be>bd):
            pari=f"✅ VICTOIRE CONFIRMÉE : {lead}"; alerte=f"Under {tot+0.5} probable"
        else: pari="⚽ EGALISATION IMMINENTE"; alerte=f"Over {tot+0.5} + BTTS"
    elif tot>=3:
        if (ad+ae)<90: pari="🥶 EQUIPES MORTES"; alerte=f"🚨 ALERTE: MOINS DE BUTS - Under {tot+0.5}"
        else: pari="💥 MATCH OUVERT - Encore 1 but"; alerte=f"Over {tot+0.5}"
    return f"⚽ {dom} {bd}-{be} {ext} ({minute}')\nPoss: {pd:.0f}%-{pe:.0f}% | Tirs: {td:.0f}-{te:.0f} | Dang: {ad:.0f}-{ae:.0f}\n{pari}\n{alerte}\nLignes:\n{pronostic_buts(tot,td+te,ad+ae)}\n──────────────────\n"

def obtenir_pronostics_live():
    ms=appel_api("/fixtures",{"live":"all"})
    if ms is None: return "❌ Erreur API."
    sel=[m for m in ms if 70 <= (m["fixture"]["status"].get("elapsed") or 0) <= 85]
    if not sel: return "🔴 Aucun match entre 70e et 85e."
    msgs=["🔴 GAZO LIVE ULTIME 70-85' 🔴\n"]
    for m in sel[:8]:
        a=analyser_match(m)
        if a: msgs.append(a)
    if len(msgs)==1: return "⚠️ Pas de stats dispo."
    return "\n".join(msgs)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 GAZO LIVE ULTIME\n/live pour lancer (70-85')\n9 par jour.")
async def live(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not verifier_limite():
        await update.message.reply_text("🛑 Limite 9/j atteinte."); return
    await update.message.reply_text(f"⏳ Analyse... {lancements_du_jour}/{MAX_LANCEMENTS_PAR_JOUR}")
    res=obtenir_pronostics_live()
    await update.message.reply_text(res, disable_web_page_preview=True)
async def statut(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"📊 {lancements_du_jour}/{MAX_LANCEMENTS_PAR_JOUR}")

def run_bot():
    if not TELEGRAM_TOKEN or not API_FOOTBALL_KEY: print("Token manquant"); return
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("live", live))
    app.add_handler(CommandHandler("statut", statut))
    print("🤖 GAZO démarré")
    app.run_polling()

if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    web_app.run(host="0.0.0.0", port=port)
