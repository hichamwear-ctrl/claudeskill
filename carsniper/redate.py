"""Remet les dates a plat, sans dependre de la version de run.py.

Autonome : recupere la liste exacte des annonces de particuliers du jour
selon le site, les insere ou les redate, puis les analyse.
"""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from carsniper import engine
from carsniper.sources.twoememain import TweedehandsSource
from carsniper.storage import db

PROFILE, LEX = engine.load_config()
con = db.init()
db.load_defects(con, LEX)
sid = db.source_id(con, "2ememain")
src = TweedehandsSource(delay=2.0)
AUJ = date.today().isoformat()

# ── 1. liste du site ────────────────────────────────────────
print("Recuperation des annonces du jour (particuliers)...")
raws, off = [], 0
while off < 3000:
    d = src._get(src._params(off, private_only=True, today_only=True))
    batch = d.get("listings") or []
    if not batch:
        break
    raws += batch
    off += src.limit
    print(f"  {len(raws)} recuperees...")
    if len(batch) < src.limit:
        break
print(f"\n{len(raws)} annonces du jour selon le site\n")

# ── 2. insertion / redatation ───────────────────────────────
ins = maj = sans_prix = err = 0
ids = []
for raw in raws:
    try:
        data = src.parse(raw, seller_known="particulier")
        eid = data.get("external_id")
        if not eid:
            continue
        ids.append(eid)
        data["published_at"] = AUJ           # garanti par le filtre du site
        db.store_raw(con, sid, eid, data.get("url"), raw)
        lid, is_new = db.upsert_listing(con, sid, eid, data)
        ins += int(is_new)
        if not data.get("price_eur"):
            sans_prix += 1
    except Exception as e:
        err += 1
        if err <= 3:
            print(f"  ! {e}")

for eid in ids:
    maj += con.execute(
        "UPDATE listings SET published_at=?, seller_type='particulier' "
        "WHERE source_id=? AND external_id=?", (AUJ, sid, eid)).rowcount
con.commit()
print(f"{ins} inserees, {maj} datees du {AUJ}, {sans_prix} sans prix, {err} erreurs")

# ── 3. purge des fausses dates heritees ─────────────────────
faux = con.execute(
    "UPDATE listings SET published_at=NULL WHERE published_at=? "
    "AND external_id NOT IN (%s)" % ",".join("?" * len(ids)),
    [AUJ] + ids).rowcount if ids else 0
con.commit()
print(f"{faux} annonces faussement datees d'aujourd'hui ont ete corrigees")

# ── 4. analyse ──────────────────────────────────────────────
import run
# On reanalyse TOUTES les annonces du jour, pas seulement celles sans score :
# une modification du moteur ou de l'echelle de confiance doit se refleter
# immediatement, sinon les anciens scores restent figes.
con.execute("DELETE FROM scores WHERE listing_id IN "
            "(SELECT id FROM listings WHERE published_at=?)", (AUJ,))
con.execute("DELETE FROM valuations WHERE listing_id IN "
            "(SELECT id FROM listings WHERE published_at=?)", (AUJ,))
con.commit()

manquants = con.execute(
    """SELECT id FROM listings WHERE status='active' AND price_eur IS NOT NULL
       AND published_at = ?""", (AUJ,)).fetchall()
print(f"\nAnalyse de {len(manquants)} annonces...")
ok = e2 = 0
for r in manquants:
    try:
        run.analyse(con, r["id"], send_alert=False)
        ok += 1
    except Exception as ex:
        e2 += 1
        if e2 <= 3:
            print(f"  ! {ex}")
con.commit()
print(f"{ok} analysees, {e2} erreurs")

q = lambda s, *a: con.execute(s, a).fetchone()[0]
print(f"\n  publiees aujourd'hui   {q('SELECT COUNT(*) FROM listings WHERE published_at=?', AUJ)}")
print(f"  ... particuliers 2005+ {q('SELECT COUNT(*) FROM listings WHERE published_at=? AND seller_type=? AND year>=2005', AUJ, 'particulier')}")
print(f"  ... avec 8+ comparables {q('SELECT COUNT(*) FROM valuations v JOIN listings l ON l.id=v.listing_id WHERE l.published_at=? AND v.comparable_count>=8', AUJ)}")
print("\nLance maintenant : python run.py top 15")
