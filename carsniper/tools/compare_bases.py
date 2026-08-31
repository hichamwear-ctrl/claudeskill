"""Compare deux bases CAR SNIPER, champ par champ.

  python tools/compare_bases.py data/carsniper.ORIGINAL.db data/carsniper.RETRAITEE.db

Sert a repondre a UNE question avant de remplacer quoi que ce soit :
la correction a-t-elle ameliore 10 cas en en cassant 10 000 ?
"""
import sqlite3
import sys

A, B = sys.argv[1], sys.argv[2]
ca, cb = sqlite3.connect(A), sqlite3.connect(B)
ca.row_factory = cb.row_factory = sqlite3.Row


def q(con, sql, defaut=0):
    try:
        v = con.execute(sql).fetchone()[0]
        return v if v is not None else defaut
    except Exception:
        return defaut


def ligne(label, sql, sens=""):
    a, b = q(ca, sql), q(cb, sql)
    if isinstance(a, float) or isinstance(b, float):
        sa, sb = f"{a:.2f}", f"{b:.2f}"
        d = b - a
        sd = f"{d:+.2f}"
    else:
        sa, sb = f"{a:,}".replace(",", " "), f"{b:,}".replace(",", " ")
        d = b - a
        sd = f"{d:+,}".replace(",", " ")
    fleche = ""
    if d and sens:
        bon = (d > 0 and sens == "+") or (d < 0 and sens == "-")
        fleche = "  ✅" if bon else "  ⚠️"
    print(f"  {label:<46}{sa:>10}{sb:>12}{sd:>11}{fleche}")


print(f"AVANT : {A}\nAPRES : {B}\n")
print(f"  {'':46}{'avant':>10}{'apres':>12}{'delta':>11}")
print("  " + "─" * 79)

print("\n  IDENTIFICATION DU VEHICULE")
ligne("annonces", "SELECT COUNT(*) FROM listings")
ligne("marque+modele identifies", "SELECT COUNT(*) FROM listings WHERE vkey IS NOT NULL", "+")
ligne("sans identification", "SELECT COUNT(*) FROM listings WHERE vkey IS NULL", "-")
ligne("cles vehicule distinctes", "SELECT COUNT(DISTINCT vkey) FROM listings WHERE vkey IS NOT NULL")
ligne("cles marque|modele distinctes", "SELECT COUNT(DISTINCT vkey_loose) FROM listings WHERE vkey_loose IS NOT NULL")
ligne("classees 'utilitaire'", "SELECT COUNT(*) FROM listings WHERE vkey LIKE '%|utilitaire'", "-")
ligne("carburant 'benzine' (non normalise)", "SELECT COUNT(*) FROM listings WHERE vkey LIKE '%|benzine|%'", "-")
ligne("carburant 'essence' (canonique)", "SELECT COUNT(*) FROM listings WHERE vkey LIKE '%|essence|%'", "+")
ligne("cle fourre-tout bmw|serie", "SELECT COUNT(*) FROM listings WHERE vkey_loose='bmw|serie'", "-")
ligne("cle fourre-tout mercedes|classe", "SELECT COUNT(*) FROM listings WHERE vkey_loose='mercedes|classe'", "-")

print("\n  DETECTION DES DEFAUTS")
ligne("defauts actifs (total)", "SELECT COUNT(*) FROM listing_defects WHERE is_negated=0")
ligne("  dont 'aircon' (faux positif type)",
      "SELECT COUNT(*) FROM listing_defects ld JOIN defects d ON d.id=ld.defect_id "
      "WHERE d.code='aircon' AND ld.is_negated=0", "-")
ligne("  dont 'gearbox' (spec prise pour panne)",
      "SELECT COUNT(*) FROM listing_defects ld JOIN defects d ON d.id=ld.defect_id "
      "WHERE d.code='gearbox' AND ld.is_negated=0", "-")
ligne("  dont 'turbo'",
      "SELECT COUNT(*) FROM listing_defects ld JOIN defects d ON d.id=ld.defect_id "
      "WHERE d.code='turbo' AND ld.is_negated=0", "-")
ligne("  dont 'accident' (vrais dommages)",
      "SELECT COUNT(*) FROM listing_defects ld JOIN defects d ON d.id=ld.defect_id "
      "WHERE d.code='accident' AND ld.is_negated=0", "+")
ligne("annonces exclues du marche sain",
      "SELECT COUNT(DISTINCT ld.listing_id) FROM listing_defects ld WHERE ld.is_negated=0", "-")

print("\n  QUALITE DU MARCHE DE REFERENCE")
ligne("evaluations produites", "SELECT COUNT(*) FROM valuations")
ligne("  avec 8+ comparables", "SELECT COUNT(*) FROM valuations WHERE comparable_count>=8", "+")
ligne("  moyenne de comparables", "SELECT AVG(comparable_count) FROM valuations WHERE comparable_count>=8", "+")
ligne("  confiance marche moyenne", "SELECT AVG(confidence) FROM valuations WHERE comparable_count>=8", "+")
ligne("pool jamais controle pour defauts",
      "SELECT COUNT(*) FROM listings WHERE vkey IS NOT NULL AND enriched_at IS NULL", "-")

print("\n  DECISIONS")
ligne("scores calcules", "SELECT COUNT(*) FROM scores")
ligne("  confiance moyenne", "SELECT AVG(confidence_score) FROM scores")
ligne("au-dessus du seuil (alertables)", "SELECT COUNT(*) FROM scores WHERE tier<>'below'")
ligne("  dont GREAT", "SELECT COUNT(*) FROM scores WHERE tier='great'")
ligne("  dont SNIPER", "SELECT COUNT(*) FROM scores WHERE tier='sniper'")
ligne("ESTIMATIONS ABERRANTES a confiance >=0.5",
      "SELECT COUNT(*) FROM listings l "
      "JOIN valuations v ON v.id=(SELECT id FROM valuations WHERE listing_id=l.id "
      "ORDER BY computed_at DESC LIMIT 1) "
      "JOIN scores s ON s.id=(SELECT id FROM scores WHERE listing_id=l.id "
      "ORDER BY computed_at DESC LIMIT 1) "
      "WHERE COALESCE(v.value_pmin,v.value_p25) > l.price_eur*3 "
      "AND s.confidence_score>=0.5", "-")
ligne("decisions tracees", "SELECT COUNT(*) FROM decisions", "+")

print("\n  ANNONCES A DOMMAGE QUI SORTAIENT COMME BONNES AFFAIRES")
for nom, con in (("avant", ca), ("apres", cb)):
    try:
        n = con.execute("""
          SELECT COUNT(*) FROM listings l
          JOIN scores s ON s.id=(SELECT id FROM scores WHERE listing_id=l.id
                                 ORDER BY computed_at DESC LIMIT 1)
          WHERE s.tier IN ('great','sniper') AND s.confidence_score>=0.5
            AND (lower(l.title) LIKE '%schade%' OR lower(l.title) LIKE '%ongeval%'
                 OR lower(l.description) LIKE '%schadewagen%')
            AND lower(l.title) NOT LIKE '%schadevrij%'""").fetchone()[0]
    except Exception:
        n = "n/a"
    print(f"    {nom:<8} {n}")
