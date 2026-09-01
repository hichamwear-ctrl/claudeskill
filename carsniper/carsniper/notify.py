"""Notification Telegram, anti-spam et formatage des alertes."""
from __future__ import annotations

import hashlib
import html
import json
import os
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def esc(v) -> str:
    """Tout texte venant du site est HOSTILE tant qu'il n'est pas echappe.

    Les messages partent en parse_mode=HTML : un simple "&" non echappe
    ("Citroen C3 1.2 Puretech S&S") fait repondre 400 a Telegram, et
    l'alerte etait alors definitivement perdue. 440 titres de la base
    reelle contiennent "&", 3 contiennent "<" ou ">".
    """
    return html.escape("" if v is None else str(v), quote=False)

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

# Emoji et libelle de chaque palier. Ils etaient codes ici ET declares
# dans profile.yaml (`tiers.*.emoji`, `tiers.*.label`) : editer le YAML ne
# changeait rien a l'ecran. La config est desormais la seule source, ces
# valeurs ne servent que de repli.
TIER_STYLE = {
    "sniper": ("🔴", "SNIPER"),
    "great": ("🟠", "GREAT DEAL"),
    "good": ("🟢", "GOOD DEAL"),
    "watch": ("🔵", "À REGARDER"),
}


def style_palier(tier: str, profile: dict | None = None) -> tuple[str, str]:
    cfg = ((profile or {}).get("tiers") or {}).get(tier) or {}
    defaut = TIER_STYLE.get(tier, ("⚪", "DEAL"))
    return (cfg.get("emoji") or defaut[0], cfg.get("label") or defaut[1])


def telegram_configure() -> bool:
    """Telegram est-il reellement configure ? Sans cela, `send` se contente
    d'afficher dans la console et renvoie None — ce qui n'est PAS un echec."""
    return bool(os.environ.get("TELEGRAM_TOKEN")
                and os.environ.get("TELEGRAM_CHAT_ID"))


class EchecTelegram(Exception):
    """Un envoi a echoue. `retry_after` porte l'attente imposee par Telegram
    sur un 429 ; `definitif` marque une erreur qu'un reessai ne corrigera
    pas (message malforme, jeton invalide, chat inconnu)."""

    def __init__(self, message: str, code: int | None = None,
                 retry_after: int = 0, definitif: bool = False):
        super().__init__(message)
        self.code = code
        self.retry_after = retry_after
        self.definitif = definitif


# Codes qu'un reessai ne corrigera jamais : inutile de boucler dessus.
CODES_DEFINITIFS = {400, 401, 403, 404}


def envoyer_strict(text: str, url: str | None = None) -> int | None:
    """Comme `send`, mais LEVE en cas d'echec au lieu de renvoyer None.

    `send` confondait "Telegram n'est pas configure" (retour None, normal)
    et "l'envoi a echoue" (retour None aussi) : l'appelant ne pouvait pas
    distinguer les deux, et une alerte perdue passait pour une alerte
    affichee en console.
    """
    token = os.environ.get("TELEGRAM_TOKEN")
    chat = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        print(text)
        return None                      # console : c'est un succes

    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=urllib.parse.urlencode(_charge(chat, text, url)).encode())
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            rep = json.loads(r.read())
        mid = (rep.get("result") or {}).get("message_id")
        if not mid:
            raise EchecTelegram(f"reponse sans message_id : {str(rep)[:120]}")
        return int(mid)
    except urllib.error.HTTPError as e:
        corps = ""
        try:
            corps = e.read().decode("utf-8", "replace")[:200]
        except Exception:
            pass
        attente = 0
        try:
            attente = int(json.loads(corps).get("parameters", {})
                          .get("retry_after", 0))
        except Exception:
            attente = int(e.headers.get("Retry-After", 0) or 0) if e.headers else 0
        raise EchecTelegram(f"HTTP {e.code} {corps}", code=e.code,
                            retry_after=attente,
                            definitif=e.code in CODES_DEFINITIFS) from e
    except Exception as e:
        raise EchecTelegram(f"{type(e).__name__}: {e}") from e


def _charge(chat: str, text: str, url: str | None) -> dict:
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
    return payload


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
    emoji, label = style_palier(res["tier"], res.get("profile"))
    val = res["valuation"]
    price = listing["price_eur"]
    mc = res.get("moins_chere")
    med = res.get("mediane")
    ecart = res.get("ecart_eur")
    ecart_pct = res.get("ecart_pct")

    L = []

    # ── la voiture ──
    ligne = f"🚗 <b>{esc((listing.get('title') or '')[:64])}</b>"
    L.append(ligne)
    meta = []
    if listing.get("year"):
        meta.append(str(listing["year"]))
    if listing.get("mileage_km"):
        meta.append(f"{int(listing['mileage_km']):,}".replace(",", " ") + " km")
    if meta:
        L.append("   " + " — ".join(meta))

    # ── ou ──
    lieu = f"📍 {esc(listing.get('location') or 'lieu inconnu')}"
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
            n = esc(DEFAUT_FR.get(d["code"], d["code"]))
            if d.get("trigger"):
                n += f" (« {esc(d['matched'])} … {esc(d['trigger'])} »)"
            elif d.get("matched"):
                n += f" (« {esc(d['matched'])} »)"
            noms.append(n)
        L.append(f"🔧 Défaut déclaré : {', '.join(noms[:3])}")

    # ── sur quoi porte la comparaison ──
    cfg = _config_lisible(listing.get("vkey"))
    if cfg:
        L.append(f"➡️ Même configuration : {esc(cfg)}")

    # ── ce qui limite la confiance : jamais masque ──
    limites = res.get("confidence_limites") or []
    if limites:
        L.append("")
        L.append(f"⚠️ Fiabilité de la comparaison : {res['fiabilite']:.0%}")
        for x in limites[:3]:
            L.append(f"   • {esc(x)}")
    if val.exclus:
        L.append("⚠️ Annonce(s) écartée(s) du calcul : "
                 + ", ".join(_eur(x) for x in val.exclus))
    hauts = getattr(val, "exclus_hauts", None)
    if hauts:
        # Elles restent comptées parmi les comparables : elles sont
        # seulement sorties de la médiane et de la dispersion, qu'elles
        # déformaient. L'écart au plancher, lui, n'en dépend pas.
        L.append("ℹ️ Prix très au-dessus du marché, hors statistiques : "
                 + ", ".join(_eur(x) for x in hauts[:3]))

    if res.get("risk", 100) < 60:
        L.append(f"🚨 Signaux de prudence sur l'annonce ({res['risk']:.0f}/100)")

    if res.get("checklist"):
        L.append("")
        L.append("🔍 <b>À vérifier sur place</b>")
        for c in list(dict.fromkeys(res["checklist"]))[:3]:
            L.append(f"   • {esc(c)}")

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
             AND a.trigger_reason IS NOT 'digest'
             AND l.price_eur = ?
             AND SUBSTR(LOWER(l.title),1,60) = SUBSTR(LOWER(?),1,60)
             AND COALESCE(l.vkey,'') = COALESCE(?,'')
             AND COALESCE(l.year,-1) = COALESCE(?,-1)
             -- Le KILOMETRAGE manquait a la signature : deux voitures
             -- reellement differentes au titre generique ("Toyota Aygo"),
             -- meme prix et meme annee, etaient prises pour une
             -- republication et la seconde etait supprimee. 369 groupes
             -- de ce type dans la base reelle.
             AND COALESCE(l.mileage_km,-1) = COALESCE(?,-1)
             AND a.sent_at >= datetime('now', ?)
           LIMIT 1""",
        (listing_id, ref["price_eur"], ref["title"], ref["vkey"], ref["year"],
         ref["mileage_km"], f"-{int(heures)} hours")).fetchone()
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

    # Le RECAP du soir ecrit lui aussi dans `alerts`, avec un score
    # possiblement bien sous le seuil (min_score 40). L'anti-spam le lisait
    # comme une vraie alerte et musselait ensuite pendant 72 h une annonce
    # qui franchissait reellement 70. Un recapitulatif n'est pas une alerte.
    last = con.execute(
        "SELECT sent_at, deal_score FROM alerts WHERE listing_id=? "
        "AND trigger_reason IS NOT 'digest' "
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


# ── FILE DE SORTIE : livraison durable des alertes ──────────────────
#
# Trois etats, chacun COMMITE immediatement :
#
#   a_envoyer      l'intention est durable, rien n'est encore parti
#   envoi_en_cours l'appel reseau est en cours -> issue INCONNUE
#   delivree       Telegram a confirme, `alerts` est ecrit
#   echec          erreur definitive (400/401/403/404), plus de reessai
#
# Un crash pendant `envoi_en_cours` laisse une ambiguite irreductible :
# Telegram n'offre aucune cle d'idempotence, donc nul ne peut savoir si le
# message est parti. On tranche pour NE PAS RENVOYER — une alerte en
# double est une regression de confiance, et l'ambiguite est TRACEE au
# lieu d'etre silencieuse.

BACKOFF_S = (0, 30, 120, 600, 1800)      # attente avant la Nieme tentative
MAX_TENTATIVES = len(BACKOFF_S)
# Telegram limite a ~1 message par seconde et par conversation. Sans cette
# pause, une rafale de 200 alertes prenait un 429 des la 20e et les
# suivantes etaient perdues.
PAUSE_ENTRE_ENVOIS_S = 1.1


def _cle_intention(con, listing_id: int, deal_score: float, prix) -> str:
    """Empreinte STABLE d'une intention d'alerte.

    Elle s'appuie sur l'identifiant du SITE, pas sur l'identifiant interne :
    un rollback SQLite annule les insertions dans `listings`, les lignes
    sont recreees avec de nouveaux `id`, et une cle fondee sur `id`
    laissait alors repartir des messages deja envoyes.
    """
    r = con.execute("SELECT external_id FROM listings WHERE id=?",
                    (listing_id,)).fetchone()
    ext = (r["external_id"] if r else None) or f"interne:{listing_id}"
    brut = f"{ext}|{round(float(deal_score or 0), 1)}|{prix}"
    return hashlib.sha256(brut.encode()).hexdigest()[:32]


def deposer(con, listing_id: int, message: str, url: str | None,
            tier: str, deal_score: float, motif: str, prix) -> int | None:
    """Rend l'intention d'alerter DURABLE, avant tout appel reseau.

    Renvoie l'id de la ligne, ou None si cette intention exacte existe
    deja (protection anti-double-alerte au niveau de la base)."""
    cle = _cle_intention(con, listing_id, deal_score, prix)
    # On VERIFIE avant d'inserer plutot que d'attraper l'IntegrityError :
    # un `rollback` ici annulerait tout le lot en cours d'ingestion, pas
    # seulement cette ligne.
    if con.execute("SELECT 1 FROM outbox WHERE cle_unique=?",
                   (cle,)).fetchone():
        return None
    cur = con.execute(
        "INSERT INTO outbox(listing_id, cle_unique, etat, tier, deal_score, "
        "motif, message, url, prochain_essai) "
        "VALUES(?,?,'a_envoyer',?,?,?,?,?,datetime('now'))",
        (listing_id, cle, tier, deal_score, motif, message, url))
    con.commit()
    return cur.lastrowid


def _ecrire_alerte(con, ligne, mid) -> None:
    con.execute(
        "INSERT INTO alerts(listing_id, tier, deal_score, trigger_reason, "
        "telegram_message_id) VALUES (?,?,?,?,?)",
        (ligne["listing_id"], ligne["tier"], ligne["deal_score"],
         ligne["motif"], mid))
    con.execute("UPDATE outbox SET etat='delivree', telegram_message_id=?, "
                "fini_le=datetime('now') WHERE id=?", (mid, ligne["id"]))
    con.commit()


def livrer(con, ligne) -> tuple[bool, str]:
    """Tente UN envoi. Chaque transition est commitee separement."""
    con.execute("UPDATE outbox SET etat='envoi_en_cours', tentatives=tentatives+1 "
                "WHERE id=?", (ligne["id"],))
    con.commit()
    try:
        mid = envoyer_strict(ligne["message"], ligne["url"])
    except EchecTelegram as e:
        attente = e.retry_after or BACKOFF_S[
            min(ligne["tentatives"], MAX_TENTATIVES - 1)]
        fini = e.definitif or ligne["tentatives"] + 1 >= MAX_TENTATIVES
        con.execute(
            "UPDATE outbox SET etat=?, derniere_erreur=?, "
            "prochain_essai=datetime('now', ?), fini_le=? WHERE id=?",
            ("echec" if fini else "a_envoyer", str(e)[:300],
             f"+{int(attente)} seconds",
             now() if fini else None, ligne["id"]))
        con.commit()
        return False, str(e)[:200]
    _ecrire_alerte(con, ligne, mid)
    return True, ""


def reprendre(con, limite: int = 200, budget_s: float = 30.0) -> dict:
    """Rejoue la file : reprises apres panne, apres 429, apres redemarrage.

    A appeler au DEBUT de chaque cycle. Les lignes restees en
    `envoi_en_cours` viennent d'un crash : leur sort est inconnu, on les
    clot sans renvoyer et on l'ecrit noir sur blanc.
    """
    bilan = {"reprises": 0, "delivrees": 0, "echecs": 0, "ambigues": 0,
             "reste": 0}

    interrompus = con.execute(
        "SELECT * FROM outbox WHERE etat='envoi_en_cours'").fetchall()
    for r in interrompus:
        con.execute(
            "UPDATE outbox SET etat='delivree', "
            "derniere_erreur='interrompu pendant l''envoi : sort inconnu, "
            "NON renvoye pour ne pas alerter deux fois', "
            "fini_le=datetime('now') WHERE id=?", (r["id"],))
        con.execute(
            "INSERT INTO alerts(listing_id, tier, deal_score, trigger_reason, "
            "telegram_message_id) VALUES (?,?,?,?,NULL)",
            (r["listing_id"], r["tier"], r["deal_score"],
             (r["motif"] or "") + "+interrompu"))
        bilan["ambigues"] += 1
    if bilan["ambigues"]:
        con.commit()
        print(f"   [outbox] {bilan['ambigues']} envoi(s) interrompu(s) par un "
              f"arret brutal : sort inconnu, NON renvoyes (voir table outbox)")

    en_attente = con.execute(
        "SELECT * FROM outbox WHERE etat='a_envoyer' "
        "AND (prochain_essai IS NULL OR prochain_essai <= datetime('now')) "
        "ORDER BY id LIMIT ?", (limite,)).fetchall()
    debut = time.monotonic()
    for i, ligne in enumerate(en_attente):
        # La file ne doit pas devenir plus longue que le cycle du radar :
        # 200 messages a 1,1 s feraient 220 s, alors que le cycle vise 90 s.
        # Ce qui reste part au cycle suivant, rien n'est perdu.
        if budget_s and time.monotonic() - debut > budget_s:
            bilan["reste"] = len(en_attente) - i
            break
        if i:
            time.sleep(PAUSE_ENTRE_ENVOIS_S)
        bilan["reprises"] += 1
        ok, err = livrer(con, ligne)
        if ok:
            bilan["delivrees"] += 1
        else:
            bilan["echecs"] += 1
            if "429" in err:
                break               # inutile d'insister dans le meme cycle
    return bilan


def en_attente(con) -> int:
    return con.execute(
        "SELECT COUNT(*) FROM outbox WHERE etat='a_envoyer'").fetchone()[0]
