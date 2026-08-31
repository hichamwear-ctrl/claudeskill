"""Mesure l'etat du moteur d'interpretation sur la base reelle.

  python tools/metrics.py [chemin_base] > avant.txt
  ... corrections ...
  python tools/metrics.py [chemin_base] > apres.txt
  diff avant.txt apres.txt

Ne modifie RIEN : relit les titres/descriptions et rejoue la detection
en memoire. C'est le filet qui garantit qu'une correction qui repare
10 cas n'en casse pas 10 000.
"""
import sys
import sqlite3
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from carsniper import engine

DB = sys.argv[1] if len(sys.argv) > 1 else "data/carsniper.db"
PROFILE, LEX = engine.load_config()
con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row

rows = con.execute(
    "SELECT id, title, description, price_eur, year, mileage_km, fuel, transmission "
    "FROM listings").fetchall()

print(f"BASE {DB} — {len(rows)} annonces")
print("=" * 62)

# ── 1. DETECTION DES DEFAUTS ────────────────────────────────
actifs, nies = Counter(), Counter()
n_avec_defaut = 0
for r in rows:
    hits = engine.detect_defects(f"{r['title'] or ''} {r['description'] or ''}", LEX)
    a = [h for h in hits if not h.negated and h.category != "modifier"]
    if a:
        n_avec_defaut += 1
    for h in hits:
        (nies if h.negated else actifs)[h.code] += 1

print("\n1) DEFAUTS ACTIFS")
for k, v in actifs.most_common():
    print(f"   {k:<16} {v:>6}")
print(f"   {'TOTAL':<16} {sum(actifs.values()):>6}")
print(f"   {'annonces a defaut':<16} {n_avec_defaut:>6}  "
      f"({n_avec_defaut / max(len(rows), 1):.0%})")
print("\n   NEGATIONS")
for k, v in nies.most_common(8):
    print(f"   {k:<16} {v:>6}")
print(f"   {'TOTAL':<16} {sum(nies.values()):>6}")

# ── 2. FORMULATIONS SENTINELLES ─────────────────────────────
print("\n2) FORMULATIONS SENTINELLES (doit / ne doit pas declencher)")
SENTINELLES = [
    ("airco",                       "aircon", False),
    ("airco kapot",                 "aircon", True),
    ("airco werkt niet",            "aircon", True),
    ("airco defect",                "aircon", True),
    ("turbo diesel",                "turbo",  False),
    ("turbo defect",                "turbo",  True),
    ("turbo kapot",                 "turbo",  True),
    ("handgeschakelde versnellingsbak", "gearbox", False),
    ("boite de vitesses manuelle",  "gearbox", False),
    ("versnellingsbak defect",      "gearbox", True),
    ("luchtvering",                 "suspension", False),
    ("luchtvering defect",          "suspension", True),
    ("disques et plaquettes neuves", "brakes", False),
    ("freins a refaire",            "brakes", True),
    ("24 kwh accu",                 "battery", False),
    ("accu defect",                 "battery", True),
    ("koppeling versleten",         "clutch", True),
    ("embrayage neuf",              "clutch", False),
    ("schadevrij",                  "accident", False),
    ("ongevalvrij",                 "accident", False),
    ("nooit schade gehad",          "accident", False),
    ("geen schade",                 "accident", False),
    ("jamais accidentee",           "accident", False),
    ("pare-choc avant repeint",     "accident", False),
    ("schadewagen",                 "accident", True),
    ("schade auto",                 "accident", True),
    ("carrosserieschade",           "accident", True),
    ("blikschade",                  "accident", True),
    ("ongeval gehad",               "accident", True),
]
bons = 0
for txt, code, attendu in SENTINELLES:
    hits = engine.detect_defects(txt, LEX)
    got = any(h.code == code and not h.negated for h in hits)
    ok = got == attendu
    bons += ok
    print(f"   {'OK ' if ok else 'ECHEC'} {txt:<34} {code:<11} "
          f"attendu={'defaut' if attendu else 'rien':<7} obtenu={'defaut' if got else 'rien'}")
print(f"   -> {bons}/{len(SENTINELLES)} correctes")

# ── 3. IDENTIFICATION DU VEHICULE ───────────────────────────
print("\n3) IDENTIFICATION DU VEHICULE")
vkeys, vloose, fuels, bodies = Counter(), Counter(), Counter(), Counter()
sans_marque = 0
for r in rows:
    v = engine.normalize_vehicle(r["title"] or "", r["description"] or "",
                                 r["year"], r["fuel"], r["transmission"])
    usable = engine.vehicle_usable(v) if hasattr(engine, "vehicle_usable") \
        else (bool(v.make and v.model) and v.confidence >= 0.55)
    if not usable:
        sans_marque += 1
        continue
    vkeys[v.key()] += 1
    vloose[f"{v.make}|{v.model}"] += 1
    fuels[str(v.fuel)] += 1
    bodies[str(v.body)] += 1
print(f"   sans identification fiable : {sans_marque:>6}  "
      f"({sans_marque / max(len(rows), 1):.0%})")
print(f"   vkey distinctes            : {len(vkeys):>6}")
print(f"   marque|modele distincts     : {len(vloose):>6}")
print("\n   CARBURANTS retenus")
for k, v in fuels.most_common():
    print(f"      {k:<32} {v:>6}")
print("\n   CARROSSERIES retenues")
for k, v in bodies.most_common():
    print(f"      {k:<32} {v:>6}")
print("\n   CLES FOURRE-TOUT (etendue de prix suspecte)")
px = {}
for r in rows:
    if not r["price_eur"]:
        continue
    v = engine.normalize_vehicle(r["title"] or "", r["description"] or "",
                                 r["year"], r["fuel"], r["transmission"])
    usable = engine.vehicle_usable(v) if hasattr(engine, "vehicle_usable") \
        else (bool(v.make and v.model) and v.confidence >= 0.55)
    if usable:
        px.setdefault(f"{v.make}|{v.model}", []).append(r["price_eur"])
sus = [(k, len(p), min(p), max(p)) for k, p in px.items()
       if len(p) >= 20 and max(p) > min(p) * 8]
for k, n, lo, hi in sorted(sus, key=lambda x: -x[1])[:8]:
    print(f"      {k:<28} n={n:<5} {lo} -> {hi} EUR")
if not sus:
    print("      aucune")

# ── 4. MOTS-CLES BRUTS EN BASE ──────────────────────────────
print("\n4) OCCURRENCES BRUTES EN BASE")
for mot in ("airco", "schadewagen", "schadevrij", "ongevalvrij",
            "versnellingsbak", "turbo", "luchtvering"):
    n = con.execute(
        "SELECT COUNT(*) FROM listings WHERE lower(title) LIKE ? "
        "OR lower(description) LIKE ?", (f"%{mot}%", f"%{mot}%")).fetchone()[0]
    print(f"   {mot:<18} {n:>6}")
con.close()
