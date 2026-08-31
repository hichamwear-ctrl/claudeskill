"""Notification Telegram, anti-spam et formatage des alertes."""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

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


def format_alert(listing: dict, res: dict, drops: int = 0,
                 age_days: float = 0) -> str:
    """Message d'alerte.

    Objectif : permettre de trancher "j'appelle ou pas" en dix secondes.
    L'ordre suit le raisonnement du mecanicien — ce que vaut la voiture,
    ce qu'elle coute vraiment, ce qui reste — et separe explicitement ce
    qui est TENU (prix affiche) de ce qui est SUPPOSE (la negociation).
    """
    emoji, label = TIER_STYLE.get(res["tier"], ("⚪", "DEAL"))
    val = res["valuation"]
    rep = res["repairs"]
    nego = res.get("negociation") or {}
    price = listing["price_eur"]
    cible = res.get("prix_negocie") or price
    ref = res.get("reference") or getattr(val, "pmin", None) or val.p50 or 0
    conf = res.get("confidence") or 0

    L = [f"{emoji} <b>{label} — {res['deal_score']:.0f}/100</b>",
         f"Confiance : <b>{_mot_confiance(conf)}</b> ({conf:.0%})",
         ""]

    L.append(f"<b>{(listing.get('title') or '')[:70]}</b>")
    meta = []
    if listing.get("year"):
        meta.append(str(listing["year"]))
    if listing.get("mileage_km"):
        meta.append(f"{int(listing['mileage_km']):,}".replace(",", " ") + " km")
    if listing.get("transmission"):
        meta.append(str(listing["transmission"]))
    if listing.get("fuel"):
        meta.append(str(listing["fuel"]))
    if meta:
        L.append(" · ".join(meta))
    lieu = []
    if listing.get("location"):
        lieu.append(f"📍 {listing['location']}")
    if listing.get("distance_km"):
        lieu.append(f"{listing['distance_km']:.0f} km")
    if lieu:
        L.append(" · ".join(lieu))

    # ── L'arithmetique, alignee ──────────────────────────────
    lignes = [
        ("Marché comparable", _eur(val.p50), f"{val.n} annonces"),
        ("Moins chère du site", _eur(ref), "← référence"),
        ("Prix affiché", _eur(price), ""),
    ]
    if nego.get("taux"):
        lignes.append(("Négo estimée", _eur(cible), f"−{nego['taux']:.0%} · hypothèse"))
    if rep.get("items"):
        lignes.append(("Réparation (toi)",
                       f"{_eur(rep['pro_low'])[:-2]}–{_eur(rep['pro_high'])}", ""))
    lignes.append(("Ton coût réel",
                   f"{_eur(res.get('true_cost_low'))[:-2]}–"
                   f"{_eur(res.get('true_cost_high'))}", ""))

    larg = max(len(a) for a, _, _ in lignes)
    largv = max(len(b) for _, b, _ in lignes)
    bloc = []
    for a, b, c in lignes:
        ligne = f"{a:<{larg}}  {b:>{largv}}"
        if c:
            ligne += f"  {c}"
        bloc.append(ligne)
    L.append("")
    L.append("<pre>" + "\n".join(bloc) + "</pre>")
    L.append("")

    # ── La marge, avec sa part hypothetique ──────────────────
    tdv = res.get("true_deal_value") or 0
    mp = res.get("margin_pct") or 0
    tenue = res.get("marge_affichee")
    L.append(f"💰 <b>MARGE ~{_eur(tdv)} ({mp:.0f} %)</b>")
    if tenue is not None and nego.get("remise"):
        if tenue > 0:
            L.append(f"   · {_eur(tenue)} tenus au prix affiché")
            L.append(f"   · {_eur(tdv - tenue)} dépendent de la négo")
        else:
            L.append("   ⚠️ nulle au prix affiché — repose entièrement "
                     "sur la remise supposée")

    # ── Le defaut, chiffre ───────────────────────────────────
    if rep.get("items"):
        L.append("")
        detail = {d["code"]: d for d in (res.get("defauts_detail") or [])
                  if not d.get("negated")}
        for code, pro, mkt in rep["items"]:
            d = detail.get(code, {})
            trouve = d.get("matched")
            if d.get("trigger"):
                trouve = f"{trouve} … {d['trigger']}"
            ded = " (déduit)" if d.get("evidence") == "component+marker" else ""
            L.append(f"🔧 <b>{code}</b>" + (f" — « {trouve} »" if trouve else "") + ded)
            L.append(f"   garage {_eur(mkt[0])[:-2]}–{_eur(mkt[1])} · "
                     f"<b>toi {_eur(pro[0])[:-2]}–{_eur(pro[1])}</b>")

    if nego.get("raisons"):
        L.append("")
        L.append("🗣️ Leviers : " + ", ".join(nego["raisons"][:3]))

    # ── Ce qui limite la confiance : jamais masque ───────────
    limites = res.get("confidence_limites") or []
    if limites:
        L.append("")
        L.append("⚠️ <b>Ce qui limite la confiance</b>")
        for x in limites[:4]:
            L.append(f"   • {x}")

    if res.get("risk", 100) < 60:
        L.append(f"🚨 Risque élevé ({res['risk']:.0f}/100)")

    if res.get("checklist"):
        L.append("")
        L.append("🔍 <b>À vérifier sur place</b>")
        for c in list(dict.fromkeys(res["checklist"]))[:4]:
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
