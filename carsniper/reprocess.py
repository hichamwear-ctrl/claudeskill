"""Retraitement complet depuis les donnees brutes.

QUATRE passes, sans aucune recollecte. L'ordre compte :

  1. RE-PARSING   les payloads bruts sont relus avec le parser courant.
  2. NORMALISATION toutes les cles vehicule sont recalculees AVANT toute
                   evaluation. Sans cette passe dediee, les premieres
                   annonces analysees cherchaient leurs comparables parmi
                   des cles issues de l'ANCIENNE normalisation : le pool
                   etait faux pour tout le debut de la base.
  3. DEFAUTS      la detection est rejouee partout, pour que le "marche
                   sain" repose sur des donnees et non sur l'absence
                   d'analyse.
  4. EVALUATION   marche, reparations, score — maintenant que les deux
                   dimensions dont depend le pool sont a jour.

A lancer apres chaque correction du parser, du lexique ou du scoring.

  python reprocess.py [chemin_base]
"""
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from carsniper import engine
from carsniper.sources.twoememain import TweedehandsSource
from carsniper.storage import db
import run

BASE = sys.argv[1] if len(sys.argv) > 1 else str(db.DB_PATH)


def _sauvegarder(chemin: str) -> str | None:
    """Copie horodatee AVANT toute reecriture.

    Le retraitement modifie la base EN PLACE : il reecrit les annonces
    depuis les payloads bruts, recalcule toutes les cles, efface et
    reconstruit les defauts et les evaluations. Sans copie prealable, une
    interruption au mauvais moment ou une regression du parser laissait
    l'utilisateur sans retour arriere possible.
    """
    src = Path(chemin)
    if not src.exists() or src.stat().st_size == 0:
        return None                      # base neuve : rien a sauvegarder
    horo = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = src.with_name(f"{src.stem}.AVANT-REPROCESS-{horo}{src.suffix}")
    shutil.copy2(src, dest)
    return str(dest)


_sauve = _sauvegarder(BASE)
if _sauve:
    print(f"Sauvegarde avant retraitement : {Path(_sauve).name}")
    print(f"   retour arriere : cp '{_sauve}' '{BASE}'\n")

con = db.init(BASE)
_, LEX = engine.load_config()
db.load_defects(con, LEX)
src = TweedehandsSource()
sid = db.source_id(con, "2ememain")
print(f"Base : {BASE}\n")


def titre(n, texte):
    print("=" * 58)
    print(f" {n}) {texte}")
    print("=" * 58)


# ═══ 1. RE-PARSING ═══
titre(1, "RE-PARSING DES DONNEES BRUTES")
raws = con.execute(
    "SELECT external_id, MAX(id) AS rid, payload_text, MIN(fetched_at) AS vu "
    "FROM raw_payloads WHERE source_id=? GROUP BY external_id", (sid,)).fetchall()
print(f"{len(raws)} payloads a relire...")
maj = err = 0
for i, r in enumerate(raws, 1):
    try:
        data = src.parse(json.loads(r["payload_text"]), fetched_at=r["vu"])
        if not data.get("external_id") or not data.get("price_eur"):
            continue
        # Retraitement DELIBERE depuis les payloads bruts : on reconstruit,
        # donc on a le droit d'effacer une valeur devenue invalide.
        db.upsert_listing(con, sid, data["external_id"], data,
                          reconstruire=True)
        maj += 1
    except Exception as e:
        err += 1
        if err <= 3:
            print(f"  ! {e}")
    if i % 10000 == 0:
        con.commit()
        print(f"  {i}/{len(raws)}")
con.commit()
print(f"{maj} annonces mises a jour, {err} erreurs\n")

# ═══ 2. NORMALISATION ═══
titre(2, "NORMALISATION DES VEHICULES")
lignes = con.execute(
    "SELECT id, title, description, year, fuel, transmission, "
    "site_model, site_body FROM listings").fetchall()
print(f"{len(lignes)} annonces a normaliser...")
identifies = 0
for i, r in enumerate(lignes, 1):
    v = engine.normalize_vehicle(r["title"] or "", r["description"] or "",
                                 r["year"], r["fuel"], r["transmission"],
                                 site_model=r["site_model"], site_body=r["site_body"])
    ok = engine.vehicle_usable(v)
    identifies += ok
    con.execute("UPDATE listings SET norm_confidence=?, vkey=?, vkey_loose=? WHERE id=?",
                (v.confidence, v.key() if ok else None,
                 f"{v.make}|{v.model}" if ok else None, r["id"]))
    if i % 10000 == 0:
        con.commit()
        print(f"  {i}/{len(lignes)}")
con.commit()
print(f"{identifies} vehicules identifies de facon fiable "
      f"({identifies / max(len(lignes), 1):.0%})\n")

# ═══ 3. DEFAUTS ═══
titre(3, "DETECTION DES DEFAUTS")
codes = {r["code"]: r["id"] for r in con.execute("SELECT id, code FROM defects")}
con.execute("DELETE FROM listing_defects")
con.execute("UPDATE listings SET enriched_at=NULL")
maintenant = db.now()
actifs = nies = 0
for i, r in enumerate(lignes, 1):
    hits = engine.detect_defects(f"{r['title'] or ''} {r['description'] or ''}", LEX)
    for h in hits:
        did = codes.get(h.code)
        if not did:
            continue
        con.execute(
            "INSERT INTO listing_defects(listing_id, defect_id, matched_text, "
            "context, is_negated, confidence) VALUES (?,?,?,?,?,?)",
            (r["id"], did, h.matched, h.context, int(h.negated), h.confidence))
        if h.negated:
            nies += 1
        else:
            actifs += 1
    # marqueur explicite : la detection a tourne sur cette annonce
    con.execute("UPDATE listings SET enriched_at=? WHERE id=?",
                (maintenant, r["id"]))
    if i % 10000 == 0:
        con.commit()
        print(f"  {i}/{len(lignes)}")
con.commit()
print(f"{actifs} defauts actifs, {nies} negations\n")

# ═══ 4. EVALUATION ═══
titre(4, "EVALUATION")
rows = con.execute("SELECT id FROM listings WHERE status='active' "
                   "AND price_eur IS NOT NULL").fetchall()
print(f"{len(rows)} annonces a evaluer...")
con.execute("DELETE FROM scores")
con.execute("DELETE FROM valuations")
con.commit()
fait = err2 = 0
for i, r in enumerate(rows, 1):
    try:
        # send_alert=False : un retraitement ne doit JAMAIS declencher
        # une rafale de notifications sur des annonces deja vues.
        run.analyse(con, r["id"], send_alert=False)
        fait += 1
    except Exception as e:
        err2 += 1
        if err2 <= 3:
            print(f"  ! {e}")
    if i % 5000 == 0:
        con.commit()
        print(f"  {i}/{len(rows)}")
con.commit()
print(f"{fait} evaluees, {err2} erreurs\n")

# ═══ 5. ETAT ═══
titre(5, "ETAT DE LA BASE")
q = lambda sql: con.execute(sql).fetchone()[0]
AUJ = "date('now','localtime')"
print(f"  total                    {q('SELECT COUNT(*) FROM listings'):>7}")
print(f"  marque identifiee        {q('SELECT COUNT(*) FROM listings WHERE vkey IS NOT NULL'):>7}")
print(f"  cles vehicule distinctes {q('SELECT COUNT(DISTINCT vkey) FROM listings WHERE vkey IS NOT NULL'):>7}")
print(f"  defauts actifs           {q('SELECT COUNT(*) FROM listing_defects WHERE is_negated=0'):>7}")
print(f"  publiees aujourd'hui     {q(f'SELECT COUNT(*) FROM listings WHERE published_at={AUJ}'):>7}")
print(f"  evaluees (8+ comp.)      {q('SELECT COUNT(*) FROM valuations WHERE comparable_count>=8'):>7}")
print(f"  au-dessus du seuil       {q('SELECT COUNT(*) FROM scores WHERE tier<>%s' % chr(39)+'below'+chr(39)):>7}")
print("\n  Configurations les mieux couvertes :")
for r in con.execute("""SELECT vkey, COUNT(*) n FROM listings
                        WHERE vkey IS NOT NULL AND status='active'
                        GROUP BY vkey ORDER BY n DESC LIMIT 8"""):
    print(f"    {r['n']:>4}  {r['vkey']}")
