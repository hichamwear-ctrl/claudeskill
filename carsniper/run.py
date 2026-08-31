#!/usr/bin/env python3
"""CAR SNIPER — orchestration.

  python run.py init        initialise la base et charge le lexique
  python run.py bootstrap   sweep complet de l'inventaire (une nuit)
  python run.py fast        RADAR : surveillance continue (~90 s)
  python run.py fast --once une seule passe
  python run.py fast --catchup  alerte aussi sur l'amorcage
  python run.py night       snapshots quotidiens + recalcul
  python run.py loop        tourne en continu (rapide + nocturne)
  python run.py top [N]     classement des meilleures annonces actives
  python run.py stats       état de la base
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import yaml

from carsniper import engine, notify
from carsniper.sources.twoememain import BlockedError, TweedehandsSource
from carsniper.storage import db

ROOT = Path(__file__).resolve().parent
PROFILE, LEXICON = engine.load_config()
COLL = PROFILE["collection"]


def _source() -> TweedehandsSource:
    """Construit le connecteur avec TOUS les reglages de profile.yaml.

    `stop_after_consecutive_errors` et `backoff_on_429_seconds` etaient
    declares dans la config et ignores au profit de valeurs codees en dur.
    """
    return TweedehandsSource(
        delay=COLL["request_delay_seconds"],
        user_agent=COLL["user_agent"],
        backoff=COLL.get("backoff_on_429_seconds", 900),
        max_consecutive_errors=COLL.get("stop_after_consecutive_errors", 12),
    )


def _age_days(iso: str | None) -> float:
    if not iso:
        return 0.0
    try:
        d = datetime.fromisoformat(iso.replace(" ", "T").replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - d).total_seconds() / 86400
    except Exception:
        return 0.0


def _est_frais(lst: dict, p: dict) -> bool:
    """L'annonce a-t-elle ete publiee dans la fenetre autorisee ?

    On se fie d'abord a la date du site. Si elle est illisible, on se rabat
    sur l'instant ou nous avons decouvert l'annonce : la boucle rapide
    tournant toutes les 90 s, une annonce vue pour la premiere fois
    aujourd'hui a ete publiee aujourd'hui.
    """
    limite = p.get("max_listing_age_days", 0)
    auj = datetime.now().date()

    pub = lst.get("published_at")
    if pub:
        try:
            d = datetime.fromisoformat(str(pub)).date()
            return (auj - d).days <= limite
        except (ValueError, TypeError):
            pass

    if not p.get("allow_first_seen_fallback"):
        return False
    vu = lst.get("first_seen_at")
    if not vu:
        return False
    try:
        d = datetime.fromisoformat(str(vu).replace(" ", "T")).date()
        return (auj - d).days <= limite
    except (ValueError, TypeError):
        return False


def _pool(con, vkey_loose: str, exclure_id: int) -> list[dict]:
    """Comparables du même modèle. Le vkey est mis en cache en base :
    on ne renormalise pas toute la base à chaque analyse.

    `exclure_id` est OBLIGATOIRE : une annonce ne doit jamais compter parmi
    ses propres comparables. Comme la référence de marché est `pmin` (la
    moyenne des 3 prix les plus bas), une annonce bon marché — précisément
    celle qu'on évalue — tirait son propre plancher vers le bas.
    """
    rows = con.execute(
        """SELECT l.price_eur, l.mileage_km, l.year, l.seller_type,
                  l.vkey, l.vkey_loose, l.norm_confidence,
                  EXISTS(SELECT 1 FROM listing_defects d WHERE d.listing_id=l.id
                         AND d.is_negated=0) AS has_defect,
                  -- "deja passee par la detection" ne peut PAS se deduire de
                  -- la presence de lignes de defauts : une annonce saine n'en
                  -- produit aucune. Il faut un marqueur explicite.
                  (l.enriched_at IS NOT NULL) AS defauts_analyses
           FROM listings l
           WHERE l.status='active' AND l.price_eur IS NOT NULL
             AND COALESCE(l.is_lease,0)=0
             AND l.vkey_loose = ? AND l.id <> ?""", (vkey_loose, exclure_id),
    ).fetchall()
    return [{
        "price_eur": r["price_eur"], "mileage_km": r["mileage_km"],
        "year": r["year"], "seller_type": r["seller_type"],
        "vkey": r["vkey"], "vkey_loose": r["vkey_loose"],
        "has_defect": bool(r["has_defect"]),
        "defauts_analyses": bool(r["defauts_analyses"]),
        "norm_confidence": r["norm_confidence"],
    } for r in rows]


def analyse(con, listing_id: int, send_alert: bool = True) -> dict | None:
    row = con.execute("SELECT * FROM listings WHERE id=?", (listing_id,)).fetchone()
    if not row or not row["price_eur"]:
        return None
    lst = dict(row)

    p = PROFILE["profile"]

    # ── TOUS les filtres ci-dessous ne concernent que l'ALERTE.
    # Une annonce hors budget ou trop lointaine doit quand meme etre
    # normalisee et valorisee : c'est un comparable. L'exclure ici la
    # privait de sa cle et amputait le marche de reference — une Golf a
    # 21 000 EUR est le meilleur comparable d'une Golf a 18 000 EUR.
    # Tous ces criteres ne concernent que l'ALERTE : l'annonce reste
    # normalisee et valorisee, car elle sert de comparable.
    alertable = True
    refus: list[str] = []

    def _refuser(motif: str):
        nonlocal alertable
        alertable = False
        refus.append(motif)

    if lst.get("is_lease"):
        _refuser("mensualite de leasing, pas un prix de vente")
    if not (p["budget_min"] <= lst["price_eur"] <= p["budget_max"]):
        _refuser(f"hors budget {p['budget_min']}-{p['budget_max']} EUR")
    if lst.get("distance_km") and lst["distance_km"] > p["max_distance_km"]:
        _refuser(f"a {lst['distance_km']:.0f} km (max {p['max_distance_km']})")
    if p.get("year_min") and (not lst.get("year") or lst["year"] < p["year_min"]):
        _refuser(f"annee < {p['year_min']}")
    if p.get("year_max") and lst.get("year") and lst["year"] > p["year_max"]:
        _refuser(f"annee > {p['year_max']}")

    vend = p.get("seller_types")
    if vend and vend != "all" and lst.get("seller_type") not in vend:
        _refuser(f"vendeur {lst.get('seller_type')}")

    # ── Criteres declares dans profile.yaml mais jamais appliques ────────
    km_max = p.get("mileage_max")
    if km_max and lst.get("mileage_km") and lst["mileage_km"] > km_max:
        _refuser(f"kilometrage > {km_max}")

    if p.get("alert_only_fresh") and alertable and not _est_frais(lst, p):
        _refuser("pas publiee aujourd'hui")

    veh = engine.normalize_vehicle(
        lst["title"] or "", lst["description"] or "",
        lst["year"], lst["fuel"], lst["transmission"],
        site_model=lst.get("site_model"), site_body=lst.get("site_body"))

    marques = p.get("brands")
    if marques and marques != "all":
        voulues = {engine.norm_text(b) for b in marques}
        if veh.make not in voulues:
            _refuser(f"marque {veh.make} hors liste")
    exclues = {engine.norm_text(b) for b in (p.get("excluded_brands") or [])}
    if veh.make and veh.make in exclues:
        _refuser(f"marque {veh.make} exclue")

    carbs = p.get("fuels")
    if carbs and carbs != "all" and veh.fuel not in {engine.norm_text(f) for f in carbs}:
        _refuser(f"carburant {veh.fuel} hors liste")
    boites = p.get("transmissions")
    if boites and boites != "all" and \
            veh.transmission not in {engine.norm_text(b) for b in boites}:
        _refuser(f"boite {veh.transmission} hors liste")

    # ── GARDE-FOU : sans marque identifiée, pas de comparables fiables.
    # Sinon toutes les annonces "Auto", "MCM", "à vendre" tombent dans le
    # même panier et le système compare une camionnette à une citadine.
    usable = bool(veh.make and veh.model) and veh.confidence >= 0.55
    vkey = veh.key() if usable else None
    vkey_loose = f"{veh.make}|{veh.model}" if usable else None
    con.execute("UPDATE listings SET norm_confidence=?, vkey=?, vkey_loose=? WHERE id=?",
                (veh.confidence, vkey, vkey_loose, listing_id))

    text = f"{lst['title'] or ''} {lst['description'] or ''}"
    hits = engine.detect_defects(text, LEXICON)
    con.execute("DELETE FROM listing_defects WHERE listing_id=?", (listing_id,))
    # Trace que la detection A TOURNE, meme si elle n'a rien trouve.
    con.execute("UPDATE listings SET enriched_at=? WHERE id=?",
                (db.now(), listing_id))
    for h in hits:
        d = con.execute("SELECT id FROM defects WHERE code=?", (h.code,)).fetchone()
        if d:
            con.execute(
                "INSERT INTO listing_defects(listing_id, defect_id, matched_text, "
                "context, is_negated, confidence) VALUES (?,?,?,?,?,?)",
                (listing_id, d["id"], h.matched, h.context, int(h.negated), h.confidence),
            )

    if usable:
        pool = _pool(con, vkey_loose, listing_id)
        target = {"year": lst["year"], "mileage_km": lst["mileage_km"],
                  "vkey": vkey, "vkey_loose": vkey_loose}
        val = engine.value_market(target, pool)
    else:
        pool, val = [], engine.Valuation()   # marque non identifiée

    snaps = [s for s in db.price_history(con, listing_id) if s["price_eur"]]
    prices = [s["price_eur"] for s in snaps]
    drops = sum(1 for a, b in zip(prices, prices[1:]) if b < a)

    # Delai depuis la derniere BAISSE : on date le snapshot qui porte le
    # nouveau prix, pas celui qui portait l'ancien.
    last_drop = None
    for i in range(len(prices) - 1, 0, -1):
        if prices[i] < prices[i - 1]:
            last_drop = _age_days(snaps[i]["observed_at"])
            break

    # Prix du tout premier releve : une baisse observee explique un prix bas
    # autrement qu'une annonce affichee d'emblee sous le marche.
    if prices:
        lst["prix_initial"] = prices[0]

    age = _age_days(lst.get("published_at") or lst.get("first_seen_at"))
    res = engine.compute_deal(lst, veh, hits, val, len(pool), age,
                              drops, last_drop, PROFILE)

    # ── mode / require_defect : declares dans profile.yaml, jamais lus ────
    actifs = [h for h in hits if not h.negated and h.category != "modifier"]
    mode = str(p.get("mode", "ALL")).upper()
    if mode == "DEFECT_ONLY" and not actifs:
        _refuser("mode DEFECT_ONLY : aucun defaut detecte")
    elif mode == "HEALTHY_ONLY" and actifs:
        _refuser("mode HEALTHY_ONLY : defaut detecte")
    if p.get("require_defect") and not actifs:
        _refuser("require_defect : aucun defaut detecte")
    res["refus_alerte"] = refus

    con.execute(
        "INSERT INTO valuations(listing_id, comparable_count, value_pmin, "
        "value_p25, value_p50, value_p75, method, confidence, comparables_json) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        (listing_id, val.n, val.pmin, val.p25, val.p50, val.p75, val.method,
         val.confidence,
         json.dumps(val.comparables, ensure_ascii=False) if val.comparables else None),
    )

    con.execute(
        "INSERT INTO scores(listing_id, deal_type, risk_score, resale_score, "
        "urgency_score, confidence_score, deal_score, tier, true_cost_low, "
        "true_cost_high, true_deal_value, margin_pct, explanation_json, "
        "weights_version) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (listing_id, res["deal_type"], res["risk"], res["resale"],
         res["urgency"], res["confidence"], res["deal_score"], res["tier"],
         res["true_cost_low"], res["true_cost_high"], res["true_deal_value"],
         res["margin_pct"], json.dumps(res["explanation"], ensure_ascii=False),
         res.get("weights_version", "")),
    )

    if send_alert and alertable and res["tier"] != "below":
        go, reason = notify.should_notify(con, listing_id, res["deal_score"],
                                          res["tier"], lst["price_eur"],
                                          PROFILE["antispam"])
        if go:
            msg = notify.format_alert(lst, res, drops, age)
            mid = notify.send(msg, lst.get("url"))
            # Une ligne dans `alerts` signifie "recu par l'utilisateur".
            # L'enregistrer alors que l'envoi a echoue empoisonnait
            # l'anti-spam : l'annonce etait ensuite bloquee 72 h alors que
            # rien n'etait jamais arrive sur le telephone.
            if mid or not notify.telegram_configure():
                con.execute(
                    "INSERT INTO alerts(listing_id, tier, deal_score, "
                    "trigger_reason, telegram_message_id) VALUES (?,?,?,?,?)",
                    (listing_id, res["tier"], res["deal_score"], reason, mid),
                )
                _tracer_decision(con, listing_id, res, mid)
            else:
                print(f"  ! envoi Telegram echoue pour #{listing_id} — "
                      f"pas d'alerte enregistree, nouvel essai au prochain tour")

    # On trace aussi les CANDIDATES NON ENVOYEES : savoir pourquoi une
    # annonce n'est PAS partie vaut autant que savoir pourquoi une autre
    # est partie. `plafonds` et `refus_json` portent la reponse.
    if alertable and (res["tier"] != "below" or res.get("plafonds")):
        deja = con.execute(
            "SELECT 1 FROM decisions WHERE listing_id=? AND envoyee=1 "
            "AND decided_at > datetime('now','-1 hour')", (listing_id,)).fetchone()
        if not deja:
            _tracer_decision(con, listing_id, res, envoyee=False)
    # On ne garde que les 5 dernieres evaluations par annonce : sans ca,
    # le recalcul nocturne de 52 000 annonces ajoute 100 000 lignes par
    # nuit et la requete de classement ralentit chaque jour.
    con.execute("DELETE FROM scores WHERE listing_id=? AND id NOT IN "
                "(SELECT id FROM scores WHERE listing_id=? "
                " ORDER BY computed_at DESC LIMIT 5)", (listing_id, listing_id))
    con.execute("DELETE FROM valuations WHERE listing_id=? AND id NOT IN "
                "(SELECT id FROM valuations WHERE listing_id=? "
                " ORDER BY computed_at DESC LIMIT 5)", (listing_id, listing_id))
    con.commit()
    return res


def _tracer_decision(con, listing_id: int, res: dict, mid=None,
                     envoyee: bool = True) -> None:
    """Fige tout ce qui a servi a decider. Une estimation importante ne doit
    pas etre une boite noire impossible a expliquer trois jours plus tard."""
    val = res.get("valuation")
    rep = res.get("repairs") or {}
    nego = res.get("negociation") or {}
    alert_id = con.execute("SELECT id FROM alerts WHERE listing_id=? "
                           "ORDER BY id DESC LIMIT 1", (listing_id,)).fetchone() \
        if envoyee else None
    j = lambda o: json.dumps(o, ensure_ascii=False)
    con.execute(
        """INSERT INTO decisions(
            listing_id, alert_id, envoyee, deal_score, tier, confidence,
            prix_affiche, prix_negocie, nego_taux, reference_key, reference_eur,
            value_pmin, value_p25, value_p50, value_p75, comparable_count,
            market_confidence, market_method, pool_verifie, iqr_ratio,
            repair_low, repair_high, true_deal_value, marge_affichee,
            part_hypothese, risk_score, defauts_json, comparables_json,
            limites_json, plafonds_json, refus_json, explication_json,
            weights_version)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (listing_id, alert_id["id"] if alert_id else None, int(envoyee),
         res.get("deal_score"), res.get("tier"), res.get("confidence"),
         res.get("listing_price"), res.get("prix_negocie"), nego.get("taux"),
         res.get("reference_key"), res.get("reference"),
         getattr(val, "pmin", None), getattr(val, "p25", None),
         getattr(val, "p50", None), getattr(val, "p75", None),
         getattr(val, "n", 0), getattr(val, "confidence", 0),
         getattr(val, "method", None), getattr(val, "pool_verifie", 0),
         getattr(val, "iqr_ratio", 0),
         rep.get("pro_low"), rep.get("pro_high"), res.get("true_deal_value"),
         res.get("marge_affichee"), res.get("part_hypothese"), res.get("risk"),
         j(res.get("defauts_detail") or []),
         j(getattr(val, "comparables", []) or []),
         j(res.get("confidence_limites") or []),
         j(res.get("plafonds") or []),
         j(res.get("refus_alerte") or []),
         j(res.get("explanation") or []),
         res.get("weights_version", "")),
    )


def _ingest(con, src, raws: list[dict], job: str,
            seller_known: str | None = None,
            date_connue: str | None = None,
            alerter: bool = True) -> tuple[int, int]:
    sid = db.source_id(con, "2ememain")
    new = 0
    rejets: dict[str, int] = {}
    for raw in raws:
        try:
            # La date de PUBLICATION vient du site ("Vandaag", "Gisteren",
            # "24 aug 26"), ancree sur la date de collecte. On ne la force
            # plus a aujourd'hui : le filtre offeredSince:Vandaag laisse
            # passer des annonces de la veille (32 sur 995 mesurees sur la
            # base reelle), et les estampiller du jour faisait alerter sur
            # des annonces qui ne sont pas nouvelles.
            data = src.parse(raw, seller_known=seller_known)
            if date_connue:
                data["published_at"] = date_connue
            if not data.get("external_id"):
                rejets["sans_id"] = rejets.get("sans_id", 0) + 1
                continue

            db.store_raw(con, sid, data["external_id"], data.get("url"), raw)

            # prix connu AVANT la mise a jour, pour detecter un changement
            av = con.execute("SELECT price_eur FROM listings WHERE source_id=? "
                             "AND external_id=?", (sid, data["external_id"])).fetchone()
            prix_avant = av["price_eur"] if av else None

            lid, is_new = db.upsert_listing(con, sid, data["external_id"], data)
            if is_new:
                new += 1

            # Sans prix ferme (Bieden, N.o.t.k.) : conservee, pas evaluee.
            if not data.get("price_eur"):
                rejets["sans_prix"] = rejets.get("sans_prix", 0) + 1
                continue

            # On re-analyse si l'annonce est nouvelle, si son prix a bouge,
            # ou si elle vient de recevoir un prix apres avoir ete "a debattre".
            # Sans ca, une baisse de 1000 EUR a 14h attendait la nuit.
            if is_new or prix_avant != data["price_eur"]:
                if not is_new:
                    rejets["prix_modifie"] = rejets.get("prix_modifie", 0) + 1
                analyse(con, lid, send_alert=alerter)
        except Exception as e:
            rejets["erreur"] = rejets.get("erreur", 0) + 1
            if rejets["erreur"] <= 3:
                print(f"  ! {e}")
    con.commit()
    if rejets:
        detail = ", ".join(f"{k}={v}" for k, v in sorted(rejets.items()))
        print(f"   (non evaluees : {detail})")
    return len(raws), new


def cmd_init():
    con = db.init()
    db.load_defects(con, LEXICON)
    print(f"Base : {db.DB_PATH}")
    print(f"Défauts chargés : {con.execute('SELECT COUNT(*) FROM defects').fetchone()[0]}")


def cmd_bootstrap():
    con = db.init()
    db.load_defects(con, LEXICON)
    src = _source()
    print("Sweep de bootstrap — plusieurs heures, laisser tourner.")
    try:
        raws = src.fetch_all(COLL["bootstrap_max_pages"])
    except BlockedError as e:
        notify.send(f"⛔ CAR SNIPER arrêté : {e}")
        return
    seen, new = _ingest(con, src, raws, "bootstrap")
    print(f"{seen} annonces vues, {new} nouvelles.")


def _numid(item_id: str) -> int:
    """Les identifiants 2ememain sont sequentiels : un numero plus eleve
    correspond a une annonce plus recente."""
    try:
        return int(str(item_id).lstrip("mM"))
    except ValueError:
        return 0


def _watermark(con, flux: str = "fast") -> int:
    """Un repere PAR FLUX. Le flux filtre (particuliers du jour) a des
    identifiants plus bas que le flux complet : partager un seul compteur
    le gelait a une valeur inatteignable."""
    r = con.execute("SELECT value FROM meta WHERE key=?",
                    (f"watermark_{flux}",)).fetchone()
    return int(r["value"]) if r else 0


def _set_watermark(con, v: int, flux: str = "fast") -> None:
    con.execute("INSERT INTO meta(key,value) VALUES(?,?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (f"watermark_{flux}", str(v)))


def _ordre_par_date(raws: list[dict]) -> bool:
    """Le lot revient-il vraiment du plus recent au plus ancien ?

    Le filigrane ne peut interrompre la pagination QUE si le flux est trie
    par date. `sortBy=SORT_INDEX` (le defaut du site) trie par pertinence :
    une annonce publiee il y a deux minutes peut alors se trouver page 12,
    et s'arreter tot ferait rater des annonces.

    On ne suppose rien : on verifie sur le lot recu que les identifiants
    decroissent (ils sont sequentiels chez 2ememain, verifie sur la base :
    aucune annonce du jour sous le plus grand identifiant de la veille).
    Quelques inversions sont tolerees — les annonces mises en avant
    remontent parfois en tete.
    """
    ids = [_numid(r.get("itemId")) for r in raws]
    ids = [i for i in ids if i]
    if len(ids) < 10:
        return False
    inversions = sum(1 for a, b in zip(ids, ids[1:]) if b > a)
    return inversions <= max(2, len(ids) // 20)


# Nombre d'annonces en fin de page qui doivent TOUTES etre sous le filigrane
# pour conclure que le flux est epuise. Absorbe les annonces isolees remontees
# par le site sans laisser passer une vraie frontiere.
QUEUE_ARRET = 10


def _collecte_du_jour(con, src, verbose: bool = True) -> tuple[list[dict], dict]:
    """Recupere les annonces du jour, en ne relisant que le necessaire.

    Retourne (annonces_brutes, diagnostic).
    """
    diag = {"pages": 0, "vues": 0, "tri_date": False, "arret": "",
            "securite": False,
            "filigrane_avant": _watermark(con, "fast"), "filigrane_apres": 0}
    securite_lue = False
    pages_max = COLL.get("fast_loop_max_pages", 30)
    filigrane = diag["filigrane_avant"]

    raws: list[dict] = []
    vus: set[str] = set()
    page = 0
    max_id = filigrane

    while page < pages_max:
        d = src._get(src._params(page * src.limit, private_only=True,
                                 today_only=True, sort=src.SORT_DATE))
        brut = d.get("listings") or []
        if not brut:
            diag["arret"] = "flux epuise"
            break
        diag["pages"] += 1
        diag["vues"] += len(brut)

        if page == 0:
            diag["tri_date"] = _ordre_par_date(brut)

        for r in brut:
            k = str(r.get("itemId") or "")
            if k and k not in vus:
                vus.add(k)
                raws.append(r)
                max_id = max(max_id, _numid(k))

        page += 1

        if len(brut) < src.limit:
            diag["arret"] = "derniere page"
            break

        # ── Arret anticipe : uniquement si le tri par date est confirme ──
        #
        # On regarde la QUEUE de la page, pas son minimum. Une annonce
        # ancienne remontee par le site (mise en avant, republication)
        # peut apparaitre n'importe ou : prendre le minimum de la page
        # faisait s'arreter des la premiere, et les pages suivantes —
        # pleines de nouveautes — n'etaient jamais lues.
        #
        # Et on lit UNE PAGE DE SECURITE au-dela avant de conclure.
        if diag["tri_date"] and filigrane:
            queue = [i for i in (_numid(r.get("itemId")) for r in brut[-QUEUE_ARRET:])
                     if i]
            if queue and all(i <= filigrane for i in queue):
                if securite_lue:
                    diag["arret"] = "filigrane atteint"
                    break
                securite_lue = True
                diag["securite"] = True

        time.sleep(src.delay)

    if not diag["arret"]:
        diag["arret"] = f"limite de {pages_max} pages"
    diag["filigrane_apres"] = max_id
    if verbose and not diag["tri_date"] and diag["filigrane_avant"]:
        print("   [tri] le flux n'est PAS trie par date : relecture complete "
              "du jour a chaque cycle (plus lent, mais rien n'est rate)")
    return raws, diag


def cmd_fast(once: bool = False, amorcage_alerte: bool = False):
    """RADAR — surveille en continu les annonces publiees aujourd'hui.

        python run.py fast            surveillance continue (~90 s)
        python run.py fast --once     une seule passe (tests, cron)
        python run.py fast --catchup  alerte aussi sur l'amorcage

    Au tout premier lancement, aucun filigrane n'existe : la passe lit tout
    le flux du jour pour etablir la reference. Elle n'ENVOIE PAS d'alerte
    (sauf --catchup), sinon le demarrage inonderait Telegram avec toutes les
    annonces deja publiees depuis minuit. Les passes suivantes ne lisent que
    les nouveautes et alertent immediatement.
    """
    con = db.init()
    src = _source()
    intervalle = COLL.get("fast_loop_seconds", 90)
    cycle = 0

    while True:
        cycle += 1
        debut = time.time()
        try:
            amorcage = _watermark(con, "fast") == 0
            raws, diag = _collecte_du_jour(con, src)

            if amorcage and not amorcage_alerte:
                print(f"[{datetime.now():%H:%M:%S}] amorcage : {len(raws)} annonces "
                      f"du jour enregistrees SANS alerte. La surveillance des "
                      f"nouveautes commence maintenant.")
                print("   (relance avec --catchup pour alerter aussi sur celles-ci)")
                seen, new = _ingest(con, src, raws, "amorcage",
                                    seller_known="particulier", alerter=False)
            else:
                seen, new = _ingest(con, src, raws, "fast_loop",
                                    seller_known="particulier")

            # Le filigrane n'avance QU'APRES une ingestion reussie : une
            # erreur au milieu ne doit pas faire sauter des annonces.
            if diag["filigrane_apres"] > diag["filigrane_avant"]:
                _set_watermark(con, diag["filigrane_apres"], "fast")
                con.commit()

            try:
                retours = notify.poll_feedback(con)
                if retours:
                    print(f"   {retours} retour(s) de feedback enregistre(s)")
            except Exception as e:
                print(f"   [feedback] ignore : {e}")

            duree = time.time() - debut
            print(f"[{datetime.now():%H:%M:%S}] cycle {cycle} : {diag['pages']} page(s), "
                  f"{seen} annonce(s) lue(s), {new} nouvelle(s)  "
                  f"({duree:.0f}s, arret : {diag['arret']})")
            if duree > intervalle:
                print(f"   [cadence] la passe a dure {duree:.0f}s pour un "
                      f"intervalle de {intervalle}s")

        except BlockedError as e:
            print(f"[{datetime.now():%H:%M:%S}] 2ememain bloque : {e} — "
                  f"pause {COLL['backoff_on_429_seconds']}s")
            if once:
                return
            time.sleep(COLL["backoff_on_429_seconds"])
            continue
        except KeyboardInterrupt:
            print("\nArrêt.")
            return
        except Exception as e:
            import traceback
            print(f"[{datetime.now():%H:%M:%S}] erreur : {type(e).__name__}: {e}")
            traceback.print_exc()
            if once:
                return
            time.sleep(min(intervalle, 60))
            continue

        if once:
            return
        time.sleep(max(1, intervalle - (time.time() - debut)))


def cmd_night(full_sweep: bool = True):
    """Snapshots + recalcul : c'est ici que naissent les meilleures alertes.

    ATTENTION : avec full_sweep=True cette passe dure plusieurs heures et la
    boucle rapide est a l'arret pendant tout ce temps. En mode 'loop' on
    n'appelle que la partie recalcul (full_sweep=False), rapide, et le sweep
    complet est a lancer separement une fois par semaine.
    """
    con = db.init()
    if not full_sweep:
        n = 0
        envoyees = 0
        maxi = COLL.get("night_max_alerts", 10)
        for r in con.execute("SELECT id FROM listings WHERE status='active'"):
            try:
                # plafond de securite : un recalcul de 52 000 annonces ne doit
                # jamais pouvoir produire une rafale de notifications
                res = analyse(con, r["id"], send_alert=(envoyees < maxi))
                if res and res.get("tier") != "below":
                    envoyees += 1
                n += 1
            except Exception:
                pass
        con.commit()
        print(f"[{datetime.now():%H:%M}] recalcul nocturne : {n} annonces")
        return

    src = _source()
    try:
        raws = src.fetch_all(COLL["bootstrap_max_pages"])
    except BlockedError as e:
        notify.send(f"CAR SNIPER en pause : {e}")
        return
    sid = db.source_id(con, "2ememain")
    seen_ids = set()
    for raw in raws:
        data = src.parse(raw)
        if data.get("external_id"):
            seen_ids.add(data["external_id"])
            db.upsert_listing(con, sid, data["external_id"], data)

    gone = con.execute(
        "SELECT id, external_id FROM listings WHERE source_id=? AND status='active'",
        (sid,)).fetchall()
    n_gone = 0
    for g in gone:
        if g["external_id"] not in seen_ids:
            con.execute("UPDATE listings SET status='gone' WHERE id=?", (g["id"],))
            db.snapshot(con, g["id"], None, "gone")
            n_gone += 1

    for r in con.execute("SELECT id FROM listings WHERE status='active'").fetchall():
        analyse(con, r["id"])
    con.commit()
    print(f"Nuit : {len(seen_ids)} actives, {n_gone} disparues")


def cmd_top(n: int = 15):
    con = db.init()
    rows = con.execute("""
        SELECT l.title, l.price_eur, l.year, l.mileage_km, l.url,
               s.deal_score, s.tier, s.true_deal_value, s.margin_pct,
               s.risk_score, s.confidence_score,
               v.comparable_count, v.value_p50
        FROM listings l
        JOIN scores s ON s.id = (SELECT id FROM scores WHERE listing_id=l.id
                                 ORDER BY computed_at DESC LIMIT 1)
        LEFT JOIN valuations v ON v.id = (SELECT id FROM valuations
                                 WHERE listing_id=l.id ORDER BY computed_at DESC LIMIT 1)
        WHERE l.status='active' AND v.comparable_count >= 8
          AND l.seller_type='particulier'
          AND l.year >= 2005
          AND l.published_at = date('now','localtime')
        ORDER BY s.deal_score DESC LIMIT :n""", {"n": n}).fetchall()
    if not rows:
        q = lambda sql, *a: con.execute(sql, a).fetchone()[0]
        tot = q("SELECT COUNT(*) FROM listings")
        sc = q("SELECT COUNT(*) FROM scores")
        dujour = q("SELECT COUNT(*) FROM listings WHERE "
                   "published_at = date('now','localtime')")
        part = q("SELECT COUNT(*) FROM listings WHERE "
                 "published_at = date('now','localtime') "
                 "AND seller_type='particulier' AND year >= 2005")
        evalu = q("SELECT COUNT(*) FROM valuations WHERE comparable_count >= 8")

        print("Aucune annonce a afficher. Diagnostic :")
        print(f"   annonces en base            {tot}")
        print(f"   evaluations enregistrees    {sc}")
        print(f"   publiees depuis minuit      {dujour}")
        print(f"   ... particuliers 2005+      {part}")
        print(f"   ... avec 8+ comparables     {evalu}")
        if sc == 0:
            print("\n-> les scores sont vides : lancer 'python reprocess.py'")
        elif dujour == 0:
            print("\n-> normal : rien n'a encore ete publie depuis minuit.")
            print("   la liste se remplira au fil de la journee.")
        elif part == 0:
            print("\n-> des annonces du jour existent mais aucune ne passe")
            print("   les filtres particulier / annee.")
        else:
            print("\n-> annonces du jour presentes mais moins de 8 comparables")
            print("   dans leur configuration exacte.")
        return
    print(f"{'':4s}{'score':>6} {'prix':>8} {'marché':>8} {'marge':>7} {'conf':>5} "
          f"{'cmp':>4}  titre")
    for i, r in enumerate(rows, 1):
        e = {"sniper": "🔴", "great": "🟠", "good": "🟢"}.get(r["tier"], "⚪")
        print(f"{i:2d}. {e} {r['deal_score']:5.1f} {r['price_eur']:>7} € "
              f"{r['value_p50'] or 0:>7} € {r['true_deal_value'] or 0:>6} € "
              f"{(r['confidence_score'] or 0):>5.0%} {r['comparable_count']:>4}  "
              f"{(r['title'] or '')[:40]}")


def cmd_digest(force: bool = False):
    """Recapitulatif du jour : les meilleures annonces, seuil ou pas."""
    cfg = PROFILE.get("digest", {}) or {}
    if not cfg.get("enabled", True) and not force:
        return
    con = db.init()
    n = cfg.get("count", 8)
    mini = cfg.get("min_score", 40)

    rows = con.execute("""
        SELECT l.title, l.price_eur, l.year, l.mileage_km, l.url, l.location,
               s.deal_score, s.tier, s.true_deal_value, s.margin_pct,
               s.risk_score, s.confidence_score,
               v.value_p25, v.comparable_count
        FROM listings l
        JOIN scores s ON s.id=(SELECT id FROM scores WHERE listing_id=l.id
                               ORDER BY computed_at DESC LIMIT 1)
        LEFT JOIN valuations v ON v.id=(SELECT id FROM valuations
                               WHERE listing_id=l.id ORDER BY computed_at DESC LIMIT 1)
        WHERE l.status='active' AND l.published_at = date('now','localtime')
          AND l.seller_type='particulier' AND l.year >= 2005
          AND COALESCE(l.is_lease,0)=0
          AND v.comparable_count >= 8 AND s.deal_score >= ?
        ORDER BY s.deal_score DESC LIMIT ?""", (mini, n)).fetchall()

    jour = con.execute(
        "SELECT COUNT(*) FROM listings WHERE published_at=date('now','localtime')"
    ).fetchone()[0]

    if not rows:
        notify.send(f"📊 <b>Récap du jour</b>\n\n{jour} annonces analysées, "
                    f"aucune au-dessus de {mini}/100.\nMarché sans opportunité "
                    f"aujourd'hui.")
        print("recap envoye (aucune opportunite)")
        return

    L = [f"📊 <b>Récap du jour — {jour} annonces analysées</b>", ""]
    for i, r in enumerate(rows, 1):
        e = {"sniper": "🔴", "great": "🟠", "good": "🟢"}.get(r["tier"], "⚪")
        marge = r["true_deal_value"] or 0
        L.append(f"{e} <b>{r['deal_score']:.0f}</b> · {(r['title'] or '')[:44]}")
        L.append(f"    {r['price_eur']} € · marché {r['value_p25'] or '?'} € · "
                 f"marge {marge} € · conf {(r['confidence_score'] or 0):.0%}")
        if r["url"]:
            L.append(f"    {r['url']}")
        L.append("")
    L.append("<i>Détail de chacune ci-dessous.</i>")
    notify.send("\n".join(L))

    # Puis chaque annonce en detail, avec ses boutons de feedback.
    if not (cfg.get("detail", True)):
        print(f"recap envoye ({len(rows)} annonces)")
        return

    ids = con.execute("""
        SELECT l.id FROM listings l
        JOIN scores s ON s.id=(SELECT id FROM scores WHERE listing_id=l.id
                               ORDER BY computed_at DESC LIMIT 1)
        LEFT JOIN valuations v ON v.id=(SELECT id FROM valuations
                               WHERE listing_id=l.id ORDER BY computed_at DESC LIMIT 1)
        WHERE l.status='active' AND l.published_at = date('now','localtime')
          AND l.seller_type='particulier' AND l.year >= 2005
          AND COALESCE(l.is_lease,0)=0
          AND v.comparable_count >= 8 AND s.deal_score >= ?
        ORDER BY s.deal_score DESC LIMIT ?""", (mini, n)).fetchall()

    envoyees = 0
    for r in ids:
        try:
            res = analyse(con, r["id"], send_alert=False)
            if not res or not res.get("valuation") or not res["valuation"].n:
                continue
            lst = dict(con.execute("SELECT * FROM listings WHERE id=?",
                                   (r["id"],)).fetchone())
            snaps = [x for x in db.price_history(con, r["id"]) if x["price_eur"]]
            prix = [x["price_eur"] for x in snaps]
            drops = sum(1 for a, b in zip(prix, prix[1:]) if b < a)
            age = _age_days(lst.get("published_at") or lst.get("first_seen_at"))

            msg = notify.format_alert(lst, res, drops, age)
            mid = notify.send(msg, lst.get("url"))
            if not mid and notify.telegram_configure():
                print(f"  ! envoi echoue pour #{r['id']}")
                continue
            con.execute(
                "INSERT INTO alerts(listing_id, tier, deal_score, trigger_reason, "
                "telegram_message_id) VALUES (?,?,?,?,?)",
                (r["id"], res["tier"], res["deal_score"], "digest", mid))
            _tracer_decision(con, r["id"], res, mid)
            envoyees += 1
            time.sleep(1.2)          # Telegram limite la cadence d'envoi
        except Exception as e:
            print(f"  ! {e}")
    con.commit()
    print(f"recap envoye : 1 resume + {envoyees} annonces detaillees")


def cmd_loop():
    """Boucle complete : radar + recalcul nocturne + recapitulatif du soir.

    Pour la seule surveillance des nouvelles annonces, `run.py fast` suffit.

    Aucune exception ne doit pouvoir l'arreter :
    l'ancienne version n'attrapait que BlockedError et KeyboardInterrupt,
    si bien qu'une erreur inattendue dans cmd_fast tuait le processus —
    et avec lui le seul endroit ou les retours Telegram etaient lus."""
    last_night = None
    last_digest = None
    echecs = 0
    while True:
        try:
            # une SEULE passe : c'est cmd_loop qui gere la cadence ici.
            cmd_fast(once=True)
            echecs = 0

            h = datetime.now().hour
            today = datetime.now().date()
            # recalcul leger uniquement : le sweep complet bloquerait la
            # boucle rapide pendant des heures
            if h == COLL["night_loop_hour"] and last_night != today:
                cmd_night(full_sweep=False)
                last_night = today

            dg = PROFILE.get("digest", {}) or {}
            if dg.get("enabled", True) and h == dg.get("hour", 19) \
                    and last_digest != today:
                cmd_digest()
                last_digest = today

        except KeyboardInterrupt:
            print("\nArrêt.")
            return
        except BlockedError as e:
            print(f"Pause {COLL['backoff_on_429_seconds']}s : {e}")
            time.sleep(COLL["backoff_on_429_seconds"])
            continue
        except Exception as e:
            # On journalise, on temporise, on continue.
            echecs += 1
            import traceback
            print(f"[{datetime.now():%H:%M:%S}] erreur ({echecs}) : "
                  f"{type(e).__name__}: {e}")
            traceback.print_exc()
            if echecs >= 10:
                notify.send(f"⛔ CAR SNIPER : {echecs} erreurs consecutives, "
                            f"derniere = {type(e).__name__}: {e}")
                echecs = 0
            time.sleep(min(60 * echecs, 900))
            continue

        time.sleep(COLL.get("fast_loop_seconds", 90))


def cmd_stats():
    con = db.init()
    for k, v in db.stats(con).items():
        print(f"  {k:12s} {v}")


if __name__ == "__main__":
    opts = set(a for a in sys.argv[2:] if a.startswith("--"))
    cmds = {"init": cmd_init, "bootstrap": cmd_bootstrap,
            "night": cmd_night, "loop": cmd_loop, "stats": cmd_stats,
            "recalc": lambda: cmd_night(full_sweep=False),
            "digest": lambda: cmd_digest(force=True)}
    arg = sys.argv[1] if len(sys.argv) > 1 else "stats"
    if arg == "fast":
        cmd_fast(once="--once" in opts, amorcage_alerte="--catchup" in opts)
    elif arg == "top":
        n = next((int(a) for a in sys.argv[2:] if a.isdigit()), 15)
        cmd_top(n)
    elif arg in cmds:
        cmds[arg]()
    else:
        print(__doc__)
