"""Bilan complet du radar sur les annonces d'une journee.

  python tools/bilan.py [chemin_base] [AAAA-MM-JJ]

Repond aux dix questions du cahier des charges : combien d'annonces
recuperees, combien exploitables, combien de notifications, la repartition
des scores, l'ecart au prix de la moins chere, et des exemples reels.
"""
import sqlite3
import statistics
import sys
from collections import Counter
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from carsniper import engine as E
from carsniper import notify
from carsniper.storage import db

BASE = sys.argv[1] if len(sys.argv) > 1 else str(db.DB_PATH)
JOUR = sys.argv[2] if len(sys.argv) > 2 else date.today().isoformat()
PROFILE, LEX = E.load_config()
p = PROFILE["profile"]
con = sqlite3.connect(BASE)
con.row_factory = sqlite3.Row


def titre(n, t):
    print("\n" + "=" * 74)
    print(f" {n}) {t}")
    print("=" * 74)


q = lambda sql, *a: con.execute(sql, a).fetchone()[0]

# ── 1. ce qui a ete recupere ──
titre(1, f"ANNONCES DU JOUR RECUPEREES  ({JOUR})")
total = q("SELECT COUNT(*) FROM listings WHERE published_at=?", JOUR)
print(f"   annonces publiees aujourd'hui en base : {total}")
print(f"   decouvertes aujourd'hui               : "
      f"{q('SELECT COUNT(*) FROM listings WHERE date(first_seen_at)=?', JOUR)}")
fw = con.execute("SELECT value FROM meta WHERE key='watermark_fast'").fetchone()
print(f"   filigrane du radar                    : {fw['value'] if fw else 'aucun'}")

# ── 2. ce qui est exploitable ──
titre(2, "VOITURES REELLEMENT EXPLOITABLES")
etapes = [
    ("avec un prix ferme", "AND price_eur IS NOT NULL"),
    ("hors leasing", "AND price_eur IS NOT NULL AND COALESCE(is_lease,0)=0"),
    ("vendeur particulier", "AND price_eur IS NOT NULL AND COALESCE(is_lease,0)=0 "
     "AND seller_type='particulier'"),
    (f"budget {p['budget_min']}-{p['budget_max']} EUR",
     f"AND price_eur BETWEEN {p['budget_min']} AND {p['budget_max']} "
     "AND COALESCE(is_lease,0)=0 AND seller_type='particulier'"),
    (f"annee >= {p['year_min']}",
     f"AND price_eur BETWEEN {p['budget_min']} AND {p['budget_max']} "
     f"AND COALESCE(is_lease,0)=0 AND seller_type='particulier' AND year>={p['year_min']}"),
    ("vehicule identifie",
     f"AND price_eur BETWEEN {p['budget_min']} AND {p['budget_max']} "
     f"AND COALESCE(is_lease,0)=0 AND seller_type='particulier' "
     f"AND year>={p['year_min']} AND vkey IS NOT NULL"),
]
prec = total
for nom, cond in etapes:
    n = q(f"SELECT COUNT(*) FROM listings WHERE published_at=? {cond}", JOUR)
    print(f"   {nom:<34}{n:>6}   {f'-{prec-n}' if prec-n > 0 else ''}")
    prec = n
candidates = prec

# ── 3 a 8. le radar ──
lignes = con.execute(f"""
    SELECT l.*, s.deal_score, s.tier, s.confidence_score,
           v.value_pmin, v.value_p50, v.comparable_count, v.method
    FROM listings l
    JOIN scores s ON s.id=(SELECT id FROM scores WHERE listing_id=l.id
                           ORDER BY computed_at DESC LIMIT 1)
    JOIN valuations v ON v.id=(SELECT id FROM valuations WHERE listing_id=l.id
                               ORDER BY computed_at DESC LIMIT 1)
    WHERE l.published_at=? AND l.price_eur BETWEEN {p['budget_min']} AND {p['budget_max']}
      AND COALESCE(l.is_lease,0)=0 AND l.seller_type='particulier'
      AND l.year>={p['year_min']} AND l.vkey IS NOT NULL
      AND v.comparable_count > 0""", (JOUR,)).fetchall()

titre(3, "COMPARABLES TROUVES")
if lignes:
    ns = [r["comparable_count"] for r in lignes]
    print(f"   annonces evaluees            : {len(lignes)} / {candidates}")
    print(f"   comparables : median {statistics.median(ns):.0f} · "
          f"min {min(ns)} · max {max(ns)}")
    print(f"   paliers utilises : "
          f"{dict(Counter('strict' if r['method'] == 'weighted_median' else 'elargi/large' for r in lignes))}")
else:
    print("   aucune annonce evaluee")

seuil = PROFILE.get("notification_threshold", 70)
alertes = [r for r in lignes if (r["deal_score"] or 0) >= seuil]

titre(4, f"NOTIFICATIONS (score >= {seuil})")
print(f"   {len(alertes)} notification(s) sur {len(lignes)} annonces evaluees")
print(f"\n   Le nombre depend UNIQUEMENT des annonces qui passent la logique :")
print(f"   aucun plafond, aucun quota, aucun objectif de volume dans le code.")

titre(5, "REPARTITION DES SCORES")
bandes = [(90, 101, "90-100  SNIPER"), (85, 90, "85-89   GREAT"),
          (75, 85, "75-84   GOOD"), (seuil, 75, f"{seuil:.0f}-74   A REGARDER"),
          (60, seuil, f"60-{seuil - 1:.0f}"), (40, 60, "40-59"), (0, 40, "0-39")]
for lo, hi, nom in bandes:
    n = sum(1 for r in lignes if lo <= (r["deal_score"] or 0) < hi)
    print(f"   {nom:<20}{n:>5}  {'#' * min(int(n / 2), 40)}")

titre(6, "ANNONCES SOUS LE PRIX DE LA MOINS CHERE COMPARABLE")
sous = [r for r in alertes if r["value_pmin"] and r["price_eur"] < r["value_pmin"]]
print(f"   {len(sous)} notification(s) affichee(s) SOUS la moins chere comparable")

titre(7, "ECART AU PRIX DE LA MOINS CHERE (notifications)")
for lo, hi, nom in [(-1000, 0, "sous la moins chere"), (0, 10, "0 a +10 %"),
                    (10, 20, "+10 a +20 %"), (20, 30, "+20 a +30 %"),
                    (30, 45, "+30 a +45 %"), (45, 10000, "au-dela de +45 %")]:
    n = 0
    for r in alertes:
        if not r["value_pmin"]:
            continue
        e = (r["price_eur"] - r["value_pmin"]) / r["value_pmin"] * 100
        if lo <= e < hi:
            n += 1
    print(f"   {nom:<26}{n:>5}")

titre(8, "SAINES / AVEC DEFAUT / ACCIDENTEES")
def defauts(lid):
    return [x["code"] for x in con.execute(
        "SELECT d.code FROM listing_defects ld JOIN defects d ON d.id=ld.defect_id "
        "WHERE ld.listing_id=? AND ld.is_negated=0 AND d.category<>'modifier'", (lid,))]
c = Counter()
tous = Counter()
for r in alertes:
    dd = defauts(r["id"])
    tous.update(dd)
    if not dd:
        c["saine"] += 1
    elif "accident" in dd:
        c["accidentee"] += 1
    else:
        c["avec defaut mecanique/autre"] += 1
for k, v in c.most_common():
    print(f"   {k:<32}{v:>5}")
if tous:
    print(f"\n   defauts presents : {dict(tous.most_common(10))}")

titre(9, "EXEMPLES REELS DE NOTIFICATIONS")
for r in sorted(alertes, key=lambda x: -(x["deal_score"] or 0))[:5]:
    pmin = r["value_pmin"] or 0
    e = r["price_eur"] - pmin
    ep = e / pmin * 100 if pmin else 0
    d = defauts(r["id"])
    dist = r["distance_km"]
    print(f"\n   {r['deal_score']:>5.0f}/100  {(r['title'] or '')[:52]}")
    print(f"           {r['price_eur']} EUR  ·  moins chere {pmin} EUR  ·  "
          f"ecart {e:+} EUR ({ep:+.0f} %)")
    print(f"           {r['comparable_count']} comparables  ·  {r['location']}"
          + (f"  ·  ~{dist:.0f} km de Bruxelles" if dist else "  ·  distance inconnue"))
    if d:
        print(f"           defaut declare : {', '.join(d)}")

titre(10, "ETAT DU RADAR")
vue = q("SELECT MAX(first_seen_at) FROM listings")
print(f"   derniere annonce collectee : {vue}")
print(f"   cadence configuree         : {PROFILE['collection']['fast_loop_seconds']} s")
print(f"   commande de surveillance   : python run.py fast")
con.close()
