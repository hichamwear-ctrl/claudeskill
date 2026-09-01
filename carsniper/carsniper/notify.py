"""Notification Telegram, anti-spam et formatage des alertes."""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

# Le code technique du defaut -> un mot que tu lis d'un coup d'oeil.
DEFAUT_FR = {
    "clutch": "embrayage", "timing": "distribution", "turbo": "turbo",
    "injectors": "injecteurs", "dpf_egr": "FAP / EGR", "suspension": "suspension",
    "starter_alt": "démarreur / alternateur", "warning_light": "voyant allumé",
    "no_ct": "contrôle technique", "gearbox": "boîte de vitesses",
    "engine": "moteur", "headgasket": "joint de culasse", "accident": "dommage / accident",
    "corrosion": "corrosion", "cosmetic": "carrosserie (esthétique)",
    "tyres": "pneus", "brakes": "freins", "battery": "batterie",
    "aircon": "climatisation", "axle": "transmission / pont", "glass": "vitrage",
    "electrical": "électricité", "unspecified": "problème non précisé",
    "as_is": "vendu en l'état", "for_parts": "pour pièces",
}

TIER_STYLE = {
    "sniper": ("🔴", "SNIPER"),
    "great": ("🟠", "GREAT DEAL"),
    "good": ("🟢", "GOOD DEAL"),
    "watch": ("🔵", "À REGARDER"),
}


def telegram_configure() -> bool:
    """Telegram est-il reellement configure ? Sans cela, `send` se contente
    d'afficher dans la console et renvoie None — ce qui n'est PAS un echec."""
    return bool(os.environ.get("TELEGRAM_TOKEN")
                and os.environ.get("TELEGRAM_CHAT_ID"))


def send(text: str, url: str | None = None) -> int | None:
    token = os.environ.get("TELEGRAM_TOKEN")
    chat = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        print(text)
        return None

    payload = {
        "chat_id": chat,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": "false",
    }
    if url:
        payload["reply_markup"] = json.dumps({
            "inline_keyboard": [
                [{"text": "🔗 Ouvrir l'annonce", "url": url}],
                [{"text": "👍", "callback_data": "fb:good"},
                 {"text": "👎", "callback_data": "fb:bad"},
                 {"text": "⭐", "callback_data": "fb:would_buy"},
                 {"text": "❌", "callback_data": "fb:not_interested"},
                 {"text": "💰", "callback_data": "fb:bought"}],
            ]
        })

    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=urllib.parse.urlencode(payload).encode(),
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            return json.loads(r.read())["result"]["message_id"]
    except Exception as e:
        print(f"[telegram] échec : {e}")
        return None


def _eur(n) -> str:
    try:
        return f"{int(round(n)):,}".replace(",", " ") + " €"
    except (TypeError, ValueError):
        return "?"


def _mot_confiance(c: float) -> str:
    """Un pourcentage seul ne dit rien. Le mot, si."""
    if c >= 0.80:
        return "élevée"
    if c >= 0.65:
        return "bonne"
    if c >= 0.50:
        return "moyenne"
    return "faible"


def _config_lisible(vkey: str | None) -> str:
    """Traduit la cle technique en une phrase comprehensible."""
    if not vkey:
        return ""
    p = vkey.split("|")
    if len(p) < 6:
        return ""
    make, model, fuel, boite, cyl, body = p[:6]
    bouts = []
    if fuel and fuel.lower() not in ("none", "?"):
        bouts.append(fuel)
    if boite and boite.lower() not in ("none", "?"):
        bouts.append(boite)
    if cyl and cyl not in ("?", "None"):
        bouts.append(f"{cyl} L")
    if body and body.lower() not in ("none", "?"):
        bouts.append(body)
    return " · ".join(bouts)


def format_alert(listing: dict, res: dict, drops: int = 0,
                 age_days: float = 0) -> str:
    """Message d'alerte — un radar de prix, lisible en dix secondes.

    Prix demande, VRAIE moins chere comparable, ecart, nombre de
    comparables, score, ville et distance. Le defaut eventuel est une
    INFORMATION : il est nomme, jamais chiffre ni soustrait du prix.
    """
    emoji, label = TIER_STYLE.get(res["tier"], ("⚪", "DEAL"))
    val = res["valuation"]
    price = listing["price_eur"]
    mc = res.get("moins_chere")
    med = res.get("mediane")
    ecart = res.get("ecart_eur")
    ecart_pct = res.get("ecart_pct")

    L = []

    # ── la voiture ──
    ligne = f"🚗 <b>{(listing.get('title') or '')[:64]}</b>"
    L.append(ligne)
    meta = []
    if listing.get("year"):
        meta.append(str(listing["year"]))
    if listing.get("mileage_km"):
        meta.append(f"{int(listing['mileage_km']):,}".replace(",", " ") + " km")
    if meta:
        L.append("   " + " — ".join(meta))

    # ── ou ──
    lieu = f"📍 {listing.get('location') or 'lieu inconnu'}"
    d = listing.get("distance_km")
    if d is not None:
        lieu += f"\n📏 Bruxelles : ~{d:.0f} km à vol d'oiseau"
    else:
        lieu += "\n📏 Distance inconnue (coordonnées absentes de l'annonce)"
    L.append(lieu)
    L.append("")

    # ── le prix, le coeur du message ──
    L.append(f"💰 <b>Prix : {_eur(price)}</b>")
    if mc:
        L.append(f"🔻 Moins chère comparable : <b>{_eur(mc)}</b>")
        if med and med != mc:
            L.append(f"📊 Médiane du marché : {_eur(med)}")
        if ecart is not None:
            if ecart > 0:
                L.append(f"📈 Écart : <b>+{_eur(ecart)} / {ecart_pct:+.0f} %</b>")
            elif ecart < 0:
                L.append(f"📉 Écart : <b>{_eur(ecart)} / {ecart_pct:+.0f} %</b>  "
                         f"(sous la moins chère)")
            else:
                L.append("🎯 <b>Au prix exact de la moins chère comparable</b>")
        L.append(f"📊 {val.n} comparables"
                 + (f" · tolérance {val.niveau}" if val.niveau != "strict" else ""))

    L.append("")
    L.append(f"🎯 <b>Score : {res['deal_score']:.0f}/100</b>  ·  {label}")

    # ── le defaut : une information, jamais un calcul ──
    actifs = [d for d in (res.get("defauts_detail") or [])
              if not d.get("negated")]
    if actifs:
        noms = []
        for d in actifs:
            n = DEFAUT_FR.get(d["code"], d["code"])
            if d.get("trigger"):
                n += f" (« {d['matched']} … {d['trigger']} »)"
            elif d.get("matched"):
                n += f" (« {d['matched']} »)"
            noms.append(n)
        L.append(f"🔧 Défaut déclaré : {', '.join(noms[:3])}")

    # ── sur quoi porte la comparaison ──
    cfg = _config_lisible(listing.get("vkey"))
    if cfg:
        L.append(f"➡️ Même configuration : {cfg}")

    # ── ce qui limite la confiance : jamais masque ──
    limites = res.get("confidence_limites") or []
    if limites:
        L.append("")
        L.append(f"⚠️ Fiabilité de la comparaison : {res['fiabilite']:.0%}")
        for x in limites[:3]:
            L.append(f"   • {x}")
    if val.exclus:
        L.append("⚠️ Annonce(s) écartée(s) du calcul : "
                 + ", ".join(_eur(x) for x in val.exclus))

    if res.get("risk", 100) < 60:
        L.append(f"🚨 Signaux de prudence sur l'annonce ({res['risk']:.0f}/100)")

    if res.get("checklist"):
        L.append("")
        L.append("🔍 <b>À vérifier sur place</b>")
        for c in list(dict.fromkeys(res["checklist"]))[:3]:
            L.append(f"   • {c}")

    pied = []
    if age_days >= 1:
        pied.append(f"🕐 {age_days:.0f} j en ligne")
    if drops:
        pied.append(f"📉 {drops} baisse{'s' if drops > 1 else ''}")
    if pied:
        L.append("")
        L.append(" · ".join(pied))

    msg = "\n".join(L)
    return msg[:3900] + "…" if len(msg) > 3900 else msg


# ── Boutons de feedback ─────────────────────────────────────

REACTIONS = {
    "good": ("👍", "Bonne alerte"),
    "bad": ("👎", "Mauvaise alerte"),
    "would_buy": ("⭐", "J'aurais acheté"),
    "not_interested": ("❌", "Pas intéressé"),
    "bought": ("💰", "Acheté"),
}


def _api(method: str, **params) -> dict:
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        return {}
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/{method}",
        data=urllib.parse.urlencode(params).encode())
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"[telegram] {method} : {e}")
        return {}


def poll_feedback(con) -> int:
    """Traite les clics sur les boutons de feedback.

    Regle : on ne confirme JAMAIS un enregistrement qui n'a pas eu lieu.
    L'ancienne version repondait "enregistre" meme quand aucune alerte ne
    correspondait au message clique — le telephone affichait une
    confirmation et la table `feedback` restait vide.
    """
    row = con.execute("SELECT value FROM meta WHERE key='tg_offset'").fetchone()
    offset = int(row["value"]) if row else 0

    d = _api("getUpdates", offset=offset + 1, timeout=0, limit=50)
    if not d.get("ok"):
        # 409 = un webhook est actif : getUpdates ne recevra jamais rien.
        if d.get("error_code") == 409:
            print("[telegram] getUpdates en conflit avec un webhook actif — "
                  "supprime le webhook pour recevoir les clics")
        return 0

    n = 0
    for up in d.get("result", []):
        offset = max(offset, up["update_id"])
        cb = up.get("callback_query")
        if not cb:
            continue
        data = cb.get("data", "")
        if not data.startswith("fb:"):
            continue
        reaction = data[3:]
        mid = cb.get("message", {}).get("message_id")

        a = con.execute("SELECT id, listing_id FROM alerts "
                        "WHERE telegram_message_id=? "
                        "ORDER BY id DESC LIMIT 1", (mid,)).fetchone()
        if a:
            # Un seul retour par alerte et par reaction : un double clic ne
            # doit pas gonfler la table.
            deja = con.execute(
                "SELECT 1 FROM feedback WHERE alert_id=? AND reaction=?",
                (a["id"], reaction)).fetchone()
            if not deja:
                con.execute(
                    "INSERT INTO feedback(alert_id, listing_id, reaction) "
                    "VALUES (?,?,?)", (a["id"], a["listing_id"], reaction))
                n += 1
            emoji, libelle = REACTIONS.get(reaction, ("✅", reaction))
            texte = f"{emoji} {libelle} — enregistré"
        else:
            # Message inconnu de la base : on le dit, on ne ment pas.
            texte = ("⚠️ Alerte introuvable en base — retour NON enregistré")
        _api("answerCallbackQuery", callback_query_id=cb["id"], text=texte)

    con.execute("INSERT INTO meta(key,value) VALUES('tg_offset',?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (str(offset),))
    con.commit()
    return n


# ── Anti-spam ───────────────────────────────────────────────

def _deja_alertee_ailleurs(con, listing_id: int, antispam: dict) -> bool:
    """La MEME voiture a-t-elle deja ete annoncee sous une autre annonce ?

    On ne se fie pas a l'identifiant du site : une republication en cree un
    nouveau. La signature est le contenu — titre, prix, configuration —,
    la meme que celle qui dedoublonne deja les comparables.
    """
    if not antispam.get("suppress_reposts", True):
        return False
    heures = antispam.get("repost_window_hours",
                          antispam.get("cooldown_hours", 72))
    ref = con.execute(
        "SELECT title, price_eur, vkey, year, mileage_km FROM listings "
        "WHERE id=?", (listing_id,)).fetchone()
    if not ref or not ref["title"] or not ref["price_eur"]:
        return False
    jumeau = con.execute(
        """SELECT 1 FROM alerts a JOIN listings l ON l.id=a.listing_id
           WHERE a.listing_id <> ?
             AND l.price_eur = ?
             AND SUBSTR(LOWER(l.title),1,60) = SUBSTR(LOWER(?),1,60)
             AND COALESCE(l.vkey,'') = COALESCE(?,'')
             AND COALESCE(l.year,-1) = COALESCE(?,-1)
             AND a.sent_at >= datetime('now', ?)
           LIMIT 1""",
        (listing_id, ref["price_eur"], ref["title"], ref["vkey"], ref["year"],
         f"-{int(heures)} hours")).fetchone()
    return jumeau is not None


def should_notify(con, listing_id: int, score: float, tier: str,
                  price: int, antispam: dict) -> tuple[bool, str]:
    if tier == "below":
        return False, ""

    # `suppress_after_reaction` etait declare dans profile.yaml mais la liste
    # etait codee en dur ici. Elle est desormais lue.
    reactions = antispam.get("suppress_after_reaction") or \
        ["not_interested", "bad"]
    marques = ",".join("?" * len(reactions))
    blocked = con.execute(
        f"SELECT 1 FROM feedback WHERE listing_id=? AND reaction IN ({marques}) "
        "LIMIT 1", (listing_id, *reactions)
    ).fetchone()
    if blocked:
        return False, ""

    last = con.execute(
        "SELECT sent_at, deal_score FROM alerts WHERE listing_id=? "
        "ORDER BY sent_at DESC LIMIT 1", (listing_id,)
    ).fetchone()
    if last is None:
        # Un vendeur republie souvent la MEME voiture sous plusieurs
        # annonces : identifiants et URL differents, mais meme titre, meme
        # prix, meme configuration. Sans ce garde-fou, une seule voiture
        # produisait quatre notifications identiques.
        if _deja_alertee_ailleurs(con, listing_id, antispam):
            return False, ""
        return True, "new"

    # Une baisse de prix significative passe AVANT le delai d'attente :
    # c'est precisement l'evenement a ne pas rater, et l'ancien ordre le
    # rendait invisible pendant 72 h.
    hist = con.execute(
        "SELECT price_eur FROM listing_snapshots WHERE listing_id=? "
        "ORDER BY observed_at DESC LIMIT 2", (listing_id,)
    ).fetchall()
    if len(hist) == 2 and hist[1]["price_eur"] and hist[0]["price_eur"]:
        if hist[1]["price_eur"] - hist[0]["price_eur"] >= antispam["renotify_on_price_drop_eur"]:
            return True, "price_drop"

    sent = datetime.fromisoformat(last["sent_at"].replace(" ", "T"))
    if sent.tzinfo is None:
        sent = sent.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) - sent < timedelta(hours=antispam["cooldown_hours"]):
        return False, ""

    if score - (last["deal_score"] or 0) >= antispam["renotify_on_score_gain"]:
        return True, "score_change"

    return False, ""
