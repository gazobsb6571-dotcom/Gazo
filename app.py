import os
import requests
from datetime import datetime, date
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

# =========================
# CONFIGURATION
# =========================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY")

API_URL = "https://v3.football.api-sports.io"
MAX_LANCEMENTS_PAR_JOUR = 9

lancements_du_jour = 0
date_compteur = date.today()


# =========================
# OUTILS
# =========================

def verifier_limite():
    global lancements_du_jour, date_compteur

    aujourd_hui = date.today()

    if aujourd_hui != date_compteur:
        date_compteur = aujourd_hui
        lancements_du_jour = 0

    if lancements_du_jour >= MAX_LANCEMENTS_PAR_JOUR:
        return False

    lancements_du_jour += 1
    return True


def appel_api(endpoint, params=None):
    headers = {
        "x-apisports-key": API_FOOTBALL_KEY
    }

    try:
        response = requests.get(
            API_URL + endpoint,
            headers=headers,
            params=params,
            timeout=15
        )

        if response.status_code != 200:
            return None

        data = response.json()
        return data.get("response", [])

    except requests.RequestException:
        return None


def valeur_statistique(statistiques, nom):
    for stat in statistiques:
        if stat.get("type") == nom:
            valeur = stat.get("value")

            if valeur is None:
                return 0

            if isinstance(valeur, str):
                valeur = valeur.replace("%", "")

            try:
                return float(valeur)
            except ValueError:
                return 0

    return 0


def obtenir_statistiques(fixture_id):
    resultat = appel_api(
        "/fixtures/statistics",
        {"fixture": fixture_id}
    )

    if not resultat or len(resultat) < 2:
        return None

    equipe_domicile = resultat[0].get("statistics", [])
    equipe_exterieure = resultat[1].get("statistics", [])

    return {
        "possession_dom": valeur_statistique(
            equipe_domicile, "Ball Possession"
        ),
        "possession_ext": valeur_statistique(
            equipe_exterieure, "Ball Possession"
        ),
        "tirs_cadres_dom": valeur_statistique(
            equipe_domicile, "Shots on Goal"
        ),
        "tirs_cadres_ext": valeur_statistique(
            equipe_exterieure, "Shots on Goal"
        ),
        "attaques_dangereuses_dom": valeur_statistique(
            equipe_domicile, "Dangerous Attacks"
        ),
        "attaques_dangereuses_ext": valeur_statistique(
            equipe_exterieure, "Dangerous Attacks"
        ),
        "corners_dom": valeur_statistique(
            equipe_domicile, "Corner Kicks"
        ),
        "corners_ext": valeur_statistique(
            equipe_exterieure, "Corner Kicks"
        ),
        "cartons_rouges_dom": valeur_statistique(
            equipe_domicile, "Red Cards"
        ),
        "cartons_rouges_ext": valeur_statistique(
            equipe_exterieure, "Red Cards"
        ),
    }


def pronostic_buts(total_buts, tirs_cadres, attaques_dangereuses):
    """
    Analyse prudente basée sur les buts déjà marqués
    et l'activité offensive observée.
    """

    lignes = [1.5, 2.5, 3.5, 4.5]
    resultats = []

    for ligne in lignes:
        if total_buts > ligne:
            conseil = "OVER déjà validé"
        elif total_buts == ligne:
            conseil = "Ligne presque validée"
        elif tirs_cadres >= 6 and attaques_dangereuses >= 100:
            conseil = "OVER possible, activité élevée"
        elif tirs_cadres <= 2 and attaques_dangereuses < 70:
            conseil = "UNDER plus prudent"
        else:
            conseil = "Match incertain"

        resultats.append(f"{ligne} buts : {conseil}")

    return "\n".join(resultats)


def analyser_match(match):
    fixture = match["fixture"]
    equipes = match["teams"]
    buts = match["goals"]
    statut = fixture["status"]

    minute = statut.get("elapsed") or 0

    domicile = equipes["home"]["name"]
    exterieur = equipes["away"]["name"]

    buts_dom = buts.get("home") or 0
    buts_ext = buts.get("away") or 0
    total_buts = buts_dom + buts_ext

    statistiques = obtenir_statistiques(fixture["id"])

    if not statistiques:
        return None

    if (
        statistiques["cartons_rouges_dom"] > 0
        or statistiques["cartons_rouges_ext"] > 0
    ):
        return None

    possession_dom = statistiques["possession_dom"]
    possession_ext = statistiques["possession_ext"]

    tirs_dom = statistiques["tirs_cadres_dom"]
    tirs_ext = statistiques["tirs_cadres_ext"]

    attaques_dom = statistiques["attaques_dangereuses_dom"]
    attaques_ext = statistiques["attaques_dangereuses_ext"]

    tirs_total = tirs_dom + tirs_ext
    attaques_total = attaques_dom + attaques_ext

    pression_dom = possession_dom + attaques_dom + tirs_dom * 5
    pression_ext = possession_ext + attaques_ext + tirs_ext * 5

    if pression_dom > pression_ext + 35:
        tendance = f"Avantage statistique : {domicile}"
        resultat = "1X"
    elif pression_ext > pression_dom + 35:
        tendance = f"Avantage statistique : {exterieur}"
        resultat = "X2"
    else:
        tendance = "Pression relativement équilibrée"
        resultat = "1X ou X2 selon le contexte"

    if buts_dom == buts_ext:
        issue = "Match nul actuellement"
    elif buts_dom > buts_ext:
        issue = f"{domicile} mène"
    else:
        issue = f"{exterieur} mène"

    analyse_buts = pronostic_buts(
        total_buts,
        tirs_total,
        attaques_total
    )

    texte = (
        f"⚽ {domicile} {buts_dom} - {buts_ext} {exterieur}\n"
        f"⏱️ Minute : {minute}'\n\n"
        f"📊 Possession : {possession_dom:.0f}% - "
        f"{possession_ext:.0f}%\n"
        f"🎯 Tirs cadrés : {tirs_dom:.0f} - {tirs_ext:.0f}\n"
        f"🔥 Attaques dangereuses : {attaques_dom:.0f} - "
        f"{attaques_ext:.0f}\n\n"
        f"🧠 Situation : {issue}\n"
        f"📈 Tendance : {tendance}\n"
        f"🔎 Double chance : {resultat}\n\n"
        f"🥅 Analyse des lignes de buts :\n"
        f"{analyse_buts}\n\n"
        f"⚠️ Pronostic statistique, sans garantie."
    )

    return texte


def obtenir_pronostics_live():
    matchs = appel_api("/fixtures", {"live": "all"})

    if matchs is None:
        return "❌ Impossible de contacter API-Football."

    selection = []

    for match in matchs:
        minute = match["fixture"]["status"].get("elapsed") or 0

        # Analyse principalement entre la 70e et la 90e minute
        if 70 <= minute <= 95:
            selection.append(match)

    if not selection:
        return "🔴 Aucun match intéressant entre la 70e et la 95e minute."

    messages = [
        "🔴 GAZO LIVE ULTIME 🔴",
        "📊 Analyse statistique des matchs en direct\n"
    ]

    # Limite pour éviter de consommer trop de requêtes API
    for match in selection[:8]:
        analyse = analyser_match(match)

        if analyse:
            messages.append(analyse)
            messages.append("\n" + "─" * 35 + "\n")

    if len(messages) == 2:
        return "⚠️ Aucun match n'a fourni assez de statistiques."

    return "\n".join(messages)


# =========================
# COMMANDES TELEGRAM
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (
        "👋 Bienvenue sur GAZO LIVE ULTIME.\n\n"
        "Utilise /live pour analyser les matchs en direct.\n"
        "Limite : 9 lancements par jour."
    )

    await update.message.reply_text(message)


async def live(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global lancements_du_jour

    if not verifier_limite():
        await update.message.reply_text(
            "🛑 Limite quotidienne atteinte.\n"
            "Reviens demain pour continuer."
        )
        return

    await update.message.reply_text(
        f"⏳ Analyse en cours...\n"
        f"Lancement {lancements_du_jour}/{MAX_LANCEMENTS_PAR_JOUR}"
    )

    resultat = obtenir_pronostics_live()

    await update.message.reply_text(
        resultat,
        disable_web_page_preview=True
    )


async def statut(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global lancements_du_jour

    await update.message.reply_text(
        f"📊 Lancements utilisés aujourd'hui : "
        f"{lancements_du_jour}/{MAX_LANCEMENTS_PAR_JOUR}"
    )


# =========================
# LANCEMENT DU BOT
# =========================

def main():
    if not TELEGRAM_TOKEN or not API_FOOTBALL_KEY:
        raise ValueError(
            "Les variables TELEGRAM_TOKEN et API_FOOTBALL_KEY "
            "doivent être configurées sur Render."
        )

    application = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .build()
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("live", live))
    application.add_handler(CommandHandler("statut", statut))

    print("🤖 GAZO LIVE ULTIME est démarré.")

    application.run_polling()


if __name__ == "__main__":
    main()
