"""Pourquoi une annonce n'a-t-elle ni kilometrage ni annee ?

LECTURE SEULE. La base est ouverte en mode `ro` : ce script ne peut RIEN
modifier, meme en cas de bug.

Il repond a une seule question, et il y repond avec la preuve : pour chaque
annonce sans kilometrage ou sans annee, le site avait-il OUI ou NON envoye
l'attribut ? La reponse est dans `raw_payloads`, qui conserve la reponse
brute du site telle qu'elle est arrivee.

  - le site ne l'a pas envoye  -> le vendeur n'a pas rempli le champ.
                                  Rien a corriger dans le bot.
  - le site l'a envoye         -> le bot a perdu la donnee. Bug a corriger,
                                  et ce script imprime les identifiants.
"""
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from carsniper.sources.twoememain import (  # noqa: E402
    ANNEE_MAX, KM_MAX, TweedehandsSource, _borne)

base = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data" / "carsniper.db"
if not base.exists():
    print(f"Base introuvable : {base}")
    raise SystemExit(1)

con = sqlite3.connect(f"file:{base}?mode=ro", uri=True)
con.row_factory = sqlite3.Row

print("=" * 70)
print(f" ATTRIBUTS MANQUANTS — {base.name}  (lecture seule)")
print("=" * 70)

tot = con.execute("SELECT COUNT(*) FROM listings").fetchone()[0]
print(f"\n{tot} annonces en base\n")

print(f"{'jour de collecte':<18}{'annonces':>9}{'sans km':>9}{'sans annee':>12}"
      f"{'non evaluables':>16}")
for r in con.execute("""
        SELECT date(first_seen_at) j, COUNT(*) n,
               SUM(mileage_km IS NULL) km, SUM(year IS NULL) an,
               SUM(mileage_km IS NULL OR year IS NULL) ko
        FROM listings GROUP BY j ORDER BY j DESC LIMIT 10"""):
    print(f"{r['j'] or '?':<18}{r['n']:>9}{r['km']:>9}{r['an']:>12}"
          f"{r['ko']:>10} ({r['ko'] / r['n']:.0%})")

# ── La question qui tranche ────────────────────────────────────────────
rows = con.execute("""
    SELECT l.id, l.external_id, l.title, l.mileage_km, l.year,
           r.payload_text, r.fetched_at
    FROM listings l
    LEFT JOIN raw_payloads r
           ON r.source_id = l.source_id AND r.external_id = l.external_id
    WHERE l.mileage_km IS NULL OR l.year IS NULL
    ORDER BY l.first_seen_at DESC LIMIT 500""").fetchall()

sans_brut = site_muet = borne = bot_perdu = 0
coupables = []
invraisemblables = []
for r in rows:
    if not r["payload_text"]:
        sans_brut += 1
        continue
    p = json.loads(r["payload_text"])
    km = TweedehandsSource._attr(p, "mileage", "kilometerstand")
    an = TweedehandsSource._attr(p, "constructionYear", "bouwjaar")
    # Le bot REFUSE volontairement une valeur invraisemblable : 999 999 est
    # la sentinelle "kilometrage non communique" du site. Confondre ce refus
    # avec une perte de donnee, c'est se denoncer soi-mêeme a tort.
    km_n = TweedehandsSource._int(km)
    an_n = TweedehandsSource._int(an)
    km_retenu = _borne(km_n, 0, KM_MAX)
    an_retenu = _borne(an_n, 1900, ANNEE_MAX)
    perdu = ((r["mileage_km"] is None and km_retenu is not None)
             or (r["year"] is None and an_retenu is not None))
    rejete = ((r["mileage_km"] is None and km_n is not None and km_retenu is None)
              or (r["year"] is None and an_n is not None and an_retenu is None))
    if perdu:
        bot_perdu += 1
        if len(coupables) < 10:
            coupables.append((r["external_id"], (r["title"] or "")[:40], km, an,
                              r["mileage_km"], r["year"]))
    elif rejete:
        borne += 1
        if len(invraisemblables) < 8:
            invraisemblables.append((r["external_id"], (r["title"] or "")[:40],
                                     km_n, an_n))
    else:
        site_muet += 1

print(f"\n--- {len(rows)} annonces sans km ou sans annee, les plus recentes ---")
print(f"  le site n'avait PAS envoye l'attribut        : {site_muet}")
print(f"  valeur envoyee mais invraisemblable, refusee : {borne}")
print(f"  le site l'avait envoye, le bot l'a perdu     : {bot_perdu}")
if sans_brut:
    print(f"  reponse brute absente (non verifiable)       : {sans_brut}")

if invraisemblables:
    print(f"\n  REFUSEES CAR HORS BORNES (km <= {KM_MAX}, annee <= {ANNEE_MAX}) :")
    for eid, titre, k, a in invraisemblables:
        print(f"   {eid}  {titre}")
        print(f"      km={k}  annee={a}")
    print("  999 999 est la valeur que le site inscrit quand le vendeur")
    print("  ne communique pas le kilometrage : la refuser est voulu.")

if bot_perdu:
    print("\n  ANNONCES CONCERNEES (site -> base) :")
    for eid, titre, km, an, bkm, ban in coupables:
        print(f"   {eid}  {titre}")
        print(f"      km    site={km!r:<12} base={bkm}")
        print(f"      annee site={an!r:<12} base={ban}")
    print("\n  -> c'est un bug d'extraction. Envoie-moi ces lignes.")
else:
    print("\n  -> aucune donnee perdue : quand le kilometrage manque, c'est")
    print("     que le VENDEUR ne l'a pas renseigne sur 2ememain. Ces")
    print("     annonces ne sont pas evaluables, c'est voulu : sans km ni")
    print("     annee, aucun comparable serieux n'est possible.")

# ── Ce que le site fournit, tous payloads confondus ────────────────────
n = km_ok = an_ok = 0
for r in con.execute("SELECT payload_text FROM raw_payloads "
                     "ORDER BY id DESC LIMIT 5000"):
    p = json.loads(r[0])
    n += 1
    km_ok += TweedehandsSource._attr(p, "mileage", "kilometerstand") is not None
    an_ok += TweedehandsSource._attr(p, "constructionYear", "bouwjaar") is not None
if n:
    print(f"\n--- taux de remplissage cote SITE ({n} reponses brutes les plus recentes) ---")
    print(f"  kilometrage fourni : {km_ok:>5} ({km_ok / n:.0%})")
    print(f"  annee fournie      : {an_ok:>5} ({an_ok / n:.0%})")

con.close()
print("=" * 70)
