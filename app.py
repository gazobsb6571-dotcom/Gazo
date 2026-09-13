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
    if not statistiques: return None
    if statistiques["cartons_rouges_dom"] > 0 or statistiques["cartons_rouges_ext"] > 0:
        return None

    poss_dom = statistiques["possession_dom"]
    poss_ext = statistiques["possession_ext"]
    tirs_dom = statistiques["tirs_cadres_dom"]
    tirs_ext = statistiques["tirs_cadres_ext"]
    att_dom = statistiques["attaques_dangereuses_dom"]
    att_ext = statistiques["attaques_dangereuses_ext"]
    corners = statistiques["corners_dom"] + statistiques["corners_ext"]
    
    tirs_total = tirs_dom + tirs_ext
    att_total = att_dom + att_ext

    # CALCUL PRESSION GAZO
    pression_dom = poss_dom + att_dom + tirs_dom * 6
    pression_ext = poss_ext + att_ext + tirs_ext * 6

    # ===== LOGIQUE IMMINENTE QUE TU VEUX =====
    pari_principal = ""
    alerte = ""

    if buts_dom == buts_ext: # MATCH NUL ACTUELLEMENT
        if pression_dom > pression_ext + 35 and poss_dom > 58:
            pari_principal = f"🔥 VICTOIRE IMMINENTE : {domicile} (1)"
        elif pression_ext > pression_dom + 35 and poss_ext > 58:
            pari_principal = f"🔥 VICTOIRE IMMINENTE : {exterieur} (2)"
        else:
            pari_principal = f"🤝 NUL IMMINENT (X) - Match bloqué"
            if total_buts >= 2:
                alerte = f"⚠️ ALERTE: MOINS DE BUTS - Reste en Under {total_buts + 0.5}"

    elif abs(buts_dom - buts_ext) == 1: # 1 BUT D'ECART
        leader = domicile if buts_dom > buts_ext else exterieur
        if (pression_dom > pression_ext + 25 and buts_dom > buts_ext) or (pression_ext > pression_dom + 25 and buts_ext > buts_dom):
            pari_principal = f"✅ VICTOIRE CONFIRMÉE : {leader} garde son avance"
            alerte = f"Under {total_buts + 0.5} possible"
        else:
            pari_principal = f"⚽ BUT EGALISATION IMMINENT - Le perdant pousse"
            alerte = f"Over {total_buts + 0.5} + BTTS OUI"

    elif total_buts >= 3: # GROS SCORE 2-2, 3-1, 4-2 etc
        if att_total < 90 and tirs_total < 5:
            pari_principal = "🥶 EQUIPES MORTES"
            alerte = f"🚨 ALERTE MOINS DE BUTS : Parie Under {total_buts + 0.5} - Il n'y aura plus rien"
        else:
            pari_principal = "💥 MATCH OUVERT"
            alerte = f"ENCORE UN BUT - Over {total_buts + 0.5} fort probable"

    analyse_buts = pronostic_buts(total_buts, tirs_total, att_total)

    texte = (
        f"⚽ {domicile} {buts_dom} - {buts_ext} {exterieur}\n"
        f"⏱️ {minute}' | Poss: {poss_dom:.0f}%-{poss_ext:.0f}% | Tirs: {tirs_dom:.0f}-{tirs_ext:.0f} | Dang: {att_dom:.0f}-{att_ext:.0f} | Corners: {corners:.0f}\n\n"
        f"{pari_principal}\n"
        f"{alerte}\n\n"
        f"🥅 Lignes:\n{analyse_buts}\n"
        f"───────────────────\n"
    )
    return texte
