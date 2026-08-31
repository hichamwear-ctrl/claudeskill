"""Controle de sante complet : cherche activement les incoherences."""
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from carsniper import engine
from carsniper.sources.twoememain import TweedehandsSource
from carsniper.storage import db
import run

PROFILE, LEX = engine.load_config()
p = PROFILE["profile"]
con = db.init()
src = TweedehandsSource(delay=1.5)
alertes = []


def ko(msg):
    alertes.append(msg)
    print(f"   [PROBLEME] {msg}")


def ok(msg):
    print(f"   [OK] {msg}")


print("=" * 66)
print(" A) COHERENCE DE LA BASE")
print("=" * 66)
q = lambda s: con.execute(s).fetchone()[0]

tot = q("SELECT COUNT(*) FROM listings")
dup = q("SELECT COUNT(*) FROM (SELECT external_id FROM listings "
        "GROUP BY external_id HAVING COUNT(*)>1)")
orph = q("SELECT COUNT(*) FROM scores s LEFT JOIN listings l ON l.id=s.listing_id "
         "WHERE l.id IS NULL")
sans_score = q("SELECT COUNT(*) FROM listings l WHERE l.status='active' "
               "AND l.price_eur IS NOT NULL "
               "AND NOT EXISTS(SELECT 1 FROM scores s WHERE s.listing_id=l.id)")
neg = q("SELECT COUNT(*) FROM listings WHERE price_eur < 0")
snap = q("SELECT COUNT(*) FROM listing_snapshots")

print(f"   annonces {tot} | snapshots {snap}")
ko(f"{dup} doublons d'external_id") if dup else ok("aucun doublon")
ko(f"{orph} scores orphelins") if orph else ok("aucun score orphelin")
ko(f"{neg} prix negatifs") if neg else ok("aucun prix negatif")
if sans_score > tot * 0.05:
    ko(f"{sans_score} annonces avec prix mais sans score")
else:
    ok(f"{sans_score} annonces non scorees (tolerable)")

print("\n" + "=" * 66)
print(" B) VALEURS DE MARCHE ABERRANTES")
print("=" * 66)
abs_ = con.execute("""
    SELECT l.title, l.price_eur, v.value_p25, v.comparable_count, s.confidence_score
    FROM listings l
    JOIN valuations v ON v.id=(SELECT id FROM valuations WHERE listing_id=l.id
                               ORDER BY computed_at DESC LIMIT 1)
    JOIN scores s ON s.id=(SELECT id FROM scores WHERE listing_id=l.id
                           ORDER BY computed_at DESC LIMIT 1)
    WHERE v.value_p25 > l.price_eur * 3 AND v.comparable_count >= 8
    ORDER BY v.value_p25 * 1.0 / l.price_eur DESC LIMIT 8""").fetchall()
if abs_:
    ko(f"{len(abs_)} estimations a plus de 3x le prix affiche")
    for r in abs_:
        print(f"      {r['price_eur']:>6}EUR vs {r['value_p25']:>6}EUR "
              f"({r['comparable_count']} comp, conf {r['confidence_score']:.0%})"
              f"  {(r['title'] or '')[:34]}")
    print("      -> soit de vraies affaires, soit des comparables mal apparies")
else:
    ok("aucune estimation delirante")

print("\n" + "=" * 66)
print(" C) LE GARDE-FOU TIENT-IL ?")
print("=" * 66)
fuite = q("SELECT COUNT(*) FROM scores WHERE confidence_score < 0.5 "
          "AND deal_score > 74")
ko(f"{fuite} scores > 74 avec confiance < 0.5") if fuite else \
    ok("aucun score eleve sur estimation faible")

print("\n" + "=" * 66)
print(" D) FILTRE DE FRAICHEUR (site vs base)")
print("=" * 66)
auj = datetime.now().date()
n_api, _ = (lambda d: (d.get("totalResultCount"), d))(
    src._get(src._params(0, limit=1, private_only=True, today_only=True)))
n_base = q(f"SELECT COUNT(*) FROM listings WHERE published_at='{auj.isoformat()}' "
           f"AND seller_type='particulier'")
print(f"   API (particuliers + Vandaag) : {n_api}")
print(f"   base (published_at = {auj}) : {n_base}")

d = src._get(src._params(0, limit=100, private_only=True, today_only=True))
dates = {}
for x in d.get("listings", []) or []:
    dates[str(x.get("date"))] = dates.get(str(x.get("date")), 0) + 1
print(f"   dates renvoyees par le filtre : {dates}")
if set(dates) - {"Vandaag"}:
    ko("le filtre renvoie des dates autres que 'Vandaag' -> fenetre glissante")
else:
    ok("le filtre ne renvoie que 'Vandaag'")

print("\n" + "=" * 66)
print(" E) LEXIQUE : NEGATIONS SUR ANNONCES REELLES")
print("=" * 66)
rows = con.execute("""SELECT l.title, l.description FROM listings l
    JOIN listing_defects d ON d.listing_id=l.id
    WHERE d.is_negated=1 ORDER BY RANDOM() LIMIT 5""").fetchall()
print(f"   {q('SELECT COUNT(*) FROM listing_defects WHERE is_negated=0')} defauts actifs, "
      f"{q('SELECT COUNT(*) FROM listing_defects WHERE is_negated=1')} nies")
for r in rows:
    txt = ((r["title"] or "") + " " + (r["description"] or ""))[:88]
    print(f"      nie: {txt}")
print("   -> verifie que ces exemples sont bien des negations")

print("\n" + "=" * 66)
print(" F) ANNONCES DISPARUES")
print("=" * 66)
gone = q("SELECT COUNT(*) FROM listings WHERE status='gone'")
vieilles = q("SELECT COUNT(*) FROM listings WHERE status='active' "
             "AND date(last_seen_at) < date('now','-3 day')")
print(f"   marquees disparues : {gone}")
if vieilles > tot * 0.5:
    ko(f"{vieilles} annonces 'actives' non revues depuis 3 jours "
       f"-> lancer 'python run.py bootstrap' pour rafraichir")
else:
    ok(f"{vieilles} annonces non revues depuis 3 jours")

print("\n" + "=" * 66)
print(f" BILAN : {len(alertes)} probleme(s)")
print("=" * 66)
for a in alertes:
    print(f"   - {a}")
if not alertes:
    print("   Aucune incoherence detectee.")
