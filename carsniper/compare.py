"""Compare, champ par champ, ce que le site publie et ce que la base contient."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from carsniper.sources.twoememain import TweedehandsSource
from carsniper.storage import db

N = int(sys.argv[1]) if len(sys.argv) > 1 else 10
con = db.init()
sid = db.source_id(con, "2ememain")
src = TweedehandsSource(delay=1.5)

print("=" * 70)
print(f" COMPARAISON SITE / BASE — {N} annonces du jour")
print("=" * 70)

d = src._get(src._params(0, limit=max(N, 20), private_only=True, today_only=True))
lst = (d.get("listings") or [])[:N]
print(f"\nTotal annonces particuliers aujourd'hui sur le site : "
      f"{d.get('totalResultCount')}\n")

absent = ecarts = ok = 0
for x in lst:
    eid = str(x.get("itemId"))
    site = src.parse(x, seller_known="particulier")
    row = con.execute("SELECT * FROM listings WHERE source_id=? AND external_id=?",
                      (sid, eid)).fetchone()

    print("-" * 70)
    print(f"{eid}  {(site['title'] or '')[:52]}")

    if not row:
        print("   ABSENTE DE LA BASE")
        absent += 1
        continue

    base = dict(row)
    champs = [("prix", "price_eur"), ("km", "mileage_km"), ("annee", "year"),
              ("carburant", "fuel"), ("boite", "transmission"),
              ("vendeur", "seller_type"), ("ville", "location")]
    diff = []
    for lib, k in champs:
        a, b = site.get(k), base.get(k)
        if isinstance(a, str) and isinstance(b, str):
            egal = a.strip().lower() == b.strip().lower()
        else:
            egal = a == b
        if not egal:
            diff.append(f"{lib}: site={a} / base={b}")

    sc = con.execute("SELECT deal_score, tier, confidence_score FROM scores "
                     "WHERE listing_id=? ORDER BY computed_at DESC LIMIT 1",
                     (base["id"],)).fetchone()
    va = con.execute("SELECT value_p25, comparable_count FROM valuations "
                     "WHERE listing_id=? ORDER BY computed_at DESC LIMIT 1",
                     (base["id"],)).fetchone()

    print(f"   prix {site['price_eur']} EUR | {site['mileage_km']} km | "
          f"{site['year']} | {site['fuel']} | {site['transmission']}")
    print(f"   date publiee : site={x.get('date')} base={base.get('published_at')}")
    if sc:
        print(f"   score {sc['deal_score']:.1f} ({sc['tier']}) "
              f"conf {sc['confidence_score']:.0%}"
              + (f" | marche {va['value_p25']} EUR sur {va['comparable_count']} comp"
                 if va and va["value_p25"] else " | non evaluee"))
    else:
        print("   pas de score")

    if diff:
        ecarts += 1
        for x2 in diff:
            print(f"   ECART  {x2}")
    else:
        ok += 1
        print("   tous les champs correspondent")

print("\n" + "=" * 70)
print(f" {ok} identiques | {ecarts} avec ecart | {absent} absentes de la base")
if absent:
    print(" -> lancer 'python run.py fast'")
if not absent and not ecarts:
    print(" Le bot voit exactement les memes donnees que le site.")
print("=" * 70)
