"""Audit du filtre de fraicheur : prouve ce qui est alertable et pourquoi."""
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from carsniper import engine
from carsniper.storage import db
import run

PROFILE, _ = engine.load_config()
p = PROFILE["profile"]
con = db.init()
auj = datetime.now().date()

print("=" * 66)
print(f" AUDIT DU FILTRE  —  aujourd'hui = {auj}")
print("=" * 66)
print(f"  max_listing_age_days : {p.get('max_listing_age_days')}   "
      f"(0 = aujourd'hui uniquement)")
print(f"  vendeurs autorises   : {p.get('seller_types')}")
print(f"  annees               : {p.get('year_min')} - {p.get('year_max')}")

print("\n" + "=" * 66)
print(" 1) ANNONCES PAR DATE DE PUBLICATION")
print("=" * 66)
for r in con.execute("""SELECT published_at, COUNT(*) n FROM listings
                        WHERE published_at IS NOT NULL
                        GROUP BY published_at ORDER BY published_at DESC LIMIT 8"""):
    d = r["published_at"]
    verdict = "ALERTABLE" if d == auj.isoformat() else "ignoree"
    print(f"   {d}   {r['n']:>6} annonces   -> {verdict}")

print("\n" + "=" * 66)
print(" 2) TEST SUR 12 ANNONCES REELLES")
print("=" * 66)
rows = con.execute("""SELECT * FROM listings WHERE status='active'
                      ORDER BY RANDOM() LIMIT 12""").fetchall()
print(f"   {'publiee':<12} {'vendeur':<12} {'an':<6} {'frais?':<8} titre")
for r in rows:
    lst = dict(r)
    frais = run._est_frais(lst, p)
    ok_v = lst.get("seller_type") in (p.get("seller_types") or [])
    ok_a = bool(lst.get("year") and lst["year"] >= p.get("year_min", 0))
    verdict = "OUI" if (frais and ok_v and ok_a) else "non"
    print(f"   {str(lst.get('published_at')):<12} {str(lst.get('seller_type')):<12} "
          f"{str(lst.get('year')):<6} {verdict:<8} {(lst.get('title') or '')[:32]}")

print("\n" + "=" * 66)
print(" 3) VERIFICATION DU BASCULEMENT A MINUIT")
print("=" * 66)
for j, lib in [(0, "publiee aujourd'hui"), (1, "publiee hier"),
               (2, "publiee avant-hier"), (20, "publiee il y a 20 jours")]:
    d = (auj - timedelta(days=j)).isoformat()
    r = run._est_frais({"published_at": d}, p)
    print(f"   {lib:<28} {d}  ->  {'ALERTABLE' if r else 'ignoree'}")
print("\n   A minuit, la date du jour change : les annonces d'hier")
print("   deviennent automatiquement non alertables. Aucune action requise.")

print("\n" + "=" * 66)
print(" 4) CE QUE TU RECEVRAIS AUJOURD'HUI")
print("=" * 66)
n = con.execute("""SELECT COUNT(*) FROM listings l
    JOIN scores s ON s.id=(SELECT id FROM scores WHERE listing_id=l.id
                           ORDER BY computed_at DESC LIMIT 1)
    WHERE l.published_at=? AND l.seller_type='particulier'
      AND l.year>=? AND s.deal_score>=?""",
    (auj.isoformat(), p.get("year_min", 2005),
     PROFILE.get("notification_threshold", 75))).fetchone()[0]
print(f"   annonces franchissant le seuil de "
      f"{PROFILE.get('notification_threshold', 75)} : {n}")
