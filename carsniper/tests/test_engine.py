"""Test du moteur sur des cas réels reconstitués."""
import sys
import tempfile
from pathlib import Path


def _tmp(nom: str) -> str:
    """Chemin temporaire PORTABLE. Les chemins /tmp/... codes en dur
    rendaient toute la suite inutilisable sous Windows."""
    return str(Path(tempfile.gettempdir()) / nom)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from carsniper.engine import (
    load_config, normalize_vehicle, detect_defects,
    value_market, compute_deal, Valuation,
    canon_fuel, vehicle_usable, score_confidence, estimate_repairs,
    score_prix, COEF_ECART, DefectHit,
)

profile, lexicon = load_config()

from carsniper.storage import db as _dbm

# La file de sortie temporise 1,1 s entre deux envois (limite Telegram).
# Inutile dans les tests : on la neutralise une fois pour toutes.
import carsniper.notify as _nfmod
_nfmod.PAUSE_ENTRE_ENVOIS_S = 0
ok = 0
fail = 0


def check(label, cond):
    global ok, fail
    if cond:
        ok += 1
        print(f"  ✅ {label}")
    else:
        fail += 1
        print(f"  ❌ {label}")


# ── 1. Normalisation : 3 écritures, même véhicule ──────────
print("\n[1] NORMALISATION")
titles = [
    "BMW 320d M Sport xDrive Automaat",
    "BMW 320 D 190CV MSPORT 4X4 automatique",
    "bmw 320d xdrive m sport dsg",
]
vs = [normalize_vehicle(t, year=2019) for t in titles]
for t, v in zip(titles, vs):
    print(f"     {t[:42]:44s} → {v.make}/{v.model} {v.fuel} {v.transmission} (conf {v.confidence})")
check("les 3 titres donnent la même marque", len({v.make for v in vs}) == 1)
check("carburant diesel détecté partout", all(v.fuel == "diesel" for v in vs))
check("boîte automatique détectée partout", all(v.transmission == "automatique" for v in vs))
check("confiance > 0.7", all(v.confidence > 0.7 for v in vs))


# ── 2. Négations : le test critique ────────────────────────
print("\n[2] NÉGATIONS (zéro faux positif toléré)")
cases = [
    ("L'embrayage commence à patiner à froid", "clutch", False),
    ("Embrayage changé récemment, facture à l'appui", "clutch", True),
    ("Embrayage neuf posé le mois dernier", "clutch", True),
    ("Distribution faite à 150.000 km", "timing", True),
    ("Distribution à faire prochainement", "timing", False),
    ("Koppeling vervangen in 2023", "clutch", True),
    ("Versnellingsbak schokt bij koud weer", "gearbox", False),
    ("Suspension pneumatique arrière s'affaisse", "suspension", False),
]
for text, code, want_negated in cases:
    hits = detect_defects(text, lexicon)
    h = next((x for x in hits if x.code == code), None)
    got = h.negated if h else None
    status = "négation" if want_negated else "défaut"
    check(f"{text[:44]:46s} → {status}", h is not None and got == want_negated)


# ── 3. Market Engine ───────────────────────────────────────
print("\n[3] MARKET ENGINE")
pool = []
for i in range(24):
    pool.append({
        "price_eur": 17500 + (i % 7) * 450 - (i % 3) * 300,
        "mileage_km": 175000 + (i % 9) * 6000,
        "year": 2016 + (i % 2),
        "vkey": "audi|a6|diesel|automatique",
        "vkey_loose": "audi|a6",
        "has_defect": False, "seller_type": "particulier",
    })
# 3 épaves qui ne doivent PAS tirer la médiane vers le bas
pool += [{**pool[0], "price_eur": 9000, "has_defect": True} for _ in range(3)]
# 1 aberrant
pool.append({**pool[0], "price_eur": 41000, "has_defect": False})

target = {"year": 2016, "mileage_km": 187000,
          "vkey": "audi|a6|diesel|automatique", "vkey_loose": "audi|a6"}
val = value_market(target, pool)
print(f"     n={val.n}  p25={val.p25}  p50={val.p50}  p75={val.p75}  conf={val.confidence}")
check("comparables trouvés", val.n >= 15)
check("épaves exclues (médiane > 15000)", val.p50 > 15000)
check("aberrant à 41000 filtré (p75 < 25000)", val.p75 < 25000)
check("confiance élevée", val.confidence >= 0.7)

print("\n[3b] DONNÉES INSUFFISANTES")
val_poor = value_market(target, pool[:3])
check("n<5 → insufficient_data", val_poor.method == "insufficient_data")
check("confiance nulle", val_poor.confidence == 0.0)


# ── 4. Scénario complet : Audi A6 à suspension ─────────────
print("\n[4] SCÉNARIO — Audi A6 C7 suspension pneumatique")
listing = {
    "title": "Audi A6 Avant 3.0 TDI quattro S-Line automatique",
    "description": (
        "Voiture complète, entretiens Audi. La suspension pneumatique arrière "
        "s'affaisse quand elle reste garée. Le garage m'annonce 2600 euros et je "
        "prefere vendre. Distribution faite a 165.000 km. Vendue en l'etat. "
        "Pneus recents, interieur cuir en tres bon etat, attelage."
    ),
    "price_eur": 11500, "mileage_km": 187000, "year": 2016, "photo_count": 12,
}
veh = normalize_vehicle(listing["title"], listing["description"], 2016)
defects = detect_defects(listing["title"] + " " + listing["description"], lexicon)

print(f"     Véhicule : {veh.make}/{veh.model} {veh.fuel} {veh.transmission} (conf {veh.confidence})")
for d in defects:
    tag = "🚫 nié" if d.negated else f"🔧 actif  garage {d.market_discount}€ / toi {d.pro_cost}€"
    print(f"     {d.code:12s} {tag}")

check("suspension détectée active", any(d.code == "suspension" and not d.negated for d in defects))
check("distribution reconnue comme NIÉE", any(d.code == "timing" and d.negated for d in defects))
check("'vendu en l'état' capté", any(d.code == "as_is" for d in defects))

res = compute_deal(listing, veh, defects, val, len(pool), age_days=0.1,
                   drops=0, last_drop_days=None, profile=profile)
print(f"\n     Marché      : {val.p50} € ({val.n} comparables, conf {val.confidence})")
print(f"     Moins chère : {res['moins_chere']} €  ·  médiane {res['mediane']} €")
print(f"     Écart       : {res['ecart_eur']:+} € ({res['ecart_pct']:+.0f} %)")
print(f"     Score prix {res['score_prix']} × fiabilité {res['fiabilite']:.0%}")
print(f"     Risk {res['risk']} · Resale {res['resale']} · Urgency {res['urgency']} · Conf {res['confidence']}")
print(f"     DEAL SCORE  : {res['deal_score']} → {res['tier'].upper()}")
for e in res["explanation"]:
    print(f"       • {e}")

check("type B (défaut déclaré)", res["deal_type"] == "B")
check("référence = plancher du marché (pmin)", res["reference"] == val.pmin)
check("l'écart au prix de la moins chère est calculé", res["ecart_eur"] is not None)
check("le score vient du prix, pas d'un calcul de réparation",
      abs(res["deal_score"] - res["score_prix"] * res["fiabilite"]) < 0.11)
check("AUCUN coût de réparation n'entre dans le score",
      "true_deal_value" not in res and "margin_pct" not in res)
check("mais le défaut reste disponible pour l'affichage",
      res["repairs"]["items"] and res["repairs"]["items"][0][0] == "suspension")
check("alerte déclenchée", res["tier"] in ("good", "great", "sniper"))
check("checklist fournie", len(res["checklist"]) > 0)


# ── 5. Garde-fou : confiance faible ────────────────────────
print("\n[5] GARDE-FOU CONFIANCE")
weak = Valuation(p25=14000, p50=16000, p75=22000, n=6, method="weighted_median", confidence=0.30)
res2 = compute_deal(listing, veh, defects, weak, 6, 0.1, 0, None, profile)
print(f"     conf={res2['confidence']} → score {res2['deal_score']}")
check("score plafonné à 74 quand confiance < 0.5", res2["deal_score"] <= 74)
check("aucune alerte envoyée", res2["tier"] == "below")


# ── 6. Urgence inversée TYPE B ─────────────────────────────
print("\n[6] URGENCE — annonce ancienne avec baisses")
res3 = compute_deal({**listing, "price_eur": 8400}, veh, defects, val,
                    len(pool), age_days=24, drops=3, last_drop_days=2, profile=profile)
print(f"     Prix 11500 → 8400 € après 3 baisses en 24 j")
print(f"     Urgency {res['urgency']} → {res3['urgency']}   |   Score {res['deal_score']} → {res3['deal_score']}")
check("urgence MONTE avec l'âge (TYPE B)", res3["urgency"] > res["urgency"])
# Le score ne dépend QUE de l'écart au prix de la moins chère : une baisse de
# prix rapproche l'annonce de la moins chère, donc ne peut que l'améliorer.
# Ici les deux prix sont déjà SOUS la moins chère, le score sature à 100.
print(f"     écart {res['ecart_pct']:+.0f} % → {res3['ecart_pct']:+.0f} %")
check("une baisse de prix améliore (ou maintient) l'écart",
      res3["ecart_pct"] <= res["ecart_pct"])
check("une baisse de prix ne peut jamais baisser le SCORE DE PRIX",
      res3["score_prix"] >= res["score_prix"])
# Le score FINAL, lui, peut baisser : à 8 400 € l'annonce se retrouve 50 %
# sous la moins chère comparable, et le garde-fou « décote inexpliquée »
# abaisse la fiabilité. Ce n'est pas le défaut qui pèse — la pénalité est
# identique avec ou sans défaut — c'est l'écart au marché qui devient
# suspect. Le motif est tracé, jamais silencieux.
check("si le score final baisse, la raison est explicitement tracée",
      res3["deal_score"] >= res["deal_score"]
      or any("sous la moins chère" in x for x in res3["confidence_limites"]))



# ═══════════════════════════════════════════════════════════
#  TESTS DE RÉGRESSION — un par bug confirmé pendant l'audit
# ═══════════════════════════════════════════════════════════

def actif(texte, code):
    """Le défaut `code` est-il détecté comme ACTIF dans ce texte ?"""
    return any(h.code == code and not h.negated
               for h in detect_defects(texte, lexicon))


# ── 7. Défaut vs caractéristique ───────────────────────────
print("\n[7] DÉFAUT vs CARACTÉRISTIQUE (le bug n°1 de l'audit)")
CAS_DEFAUTS = [
    # (texte, code, doit_etre_un_defaut)
    ("airco",                                   "aircon",     False),
    ("airco, cruise control, elektrische ramen", "aircon",    False),
    ("airco kapot",                             "aircon",     True),
    ("airco werkt niet",                        "aircon",     True),
    ("airco defect",                            "aircon",     True),
    ("turbo diesel 110 pk",                     "turbo",      False),
    ("turbo defect",                            "turbo",      True),
    ("turbo kapot",                             "turbo",      True),
    ("handgeschakelde versnellingsbak",         "gearbox",    False),
    ("boite de vitesses manuelle 6 rapports",   "gearbox",    False),
    ("versnellingsbak defect",                  "gearbox",    True),
    ("luchtvering",                             "suspension", False),
    ("luchtvering defect",                      "suspension", True),
    ("disques et plaquettes neuves",            "brakes",     False),
    ("freins a refaire",                        "brakes",     True),
    ("24 kwh accu, actieradius 130 km",         "battery",    False),
    ("accu defect",                             "battery",    True),
    ("koppeling versleten",                     "clutch",     True),
    ("embrayage neuf pose le mois dernier",     "clutch",     False),
]
for texte, code, attendu in CAS_DEFAUTS:
    check(f"{texte[:38]:40s} → {'défaut' if attendu else 'rien'} ({code})",
          actif(texte, code) == attendu)


# ── 8. Dommages : composés et négations néerlandaises ──────
print("\n[8] DOMMAGES — composés et négations NL")
CAS_DOMMAGES = [
    ("schadewagen",                    True),
    ("schade auto",                    True),
    ("carrosserieschade",              True),
    ("blikschade",                     True),
    ("ongeval gehad",                  True),
    ("auto heeft schade aan links achter", True),
    ("schadevrij",                     False),
    ("ongevalvrij",                    False),
    ("ongeval vrij, eerste eigenaar",  False),
    ("nooit schade gehad",             False),
    ("geen schade",                    False),
    ("jamais accidentee",              False),
    ("pare-choc avant repeint",        False),
    ("nouveau pare choc arriere",      False),
]
for texte, attendu in CAS_DOMMAGES:
    check(f"{texte[:38]:40s} → {'dommage' if attendu else 'rien'}",
          actif(texte, "accident") == attendu)

check("le titre seul suffit : 'Toyota Aygo 2025 schadewagen'",
      actif("Toyota Aygo X 1.0 2025 schadewagen", "accident"))


# ── 9. Normalisation du carburant ──────────────────────────
print("\n[9] CARBURANT — une seule forme canonique")
check("'Benzine' → essence", canon_fuel("Benzine") == "essence")
check("'benzine' → essence", canon_fuel("benzine") == "essence")
check("'Essence' → essence", canon_fuel("Essence") == "essence")
check("'Hybride elektrisch/benzine' → hybride",
      canon_fuel("Hybride elektrisch/benzine") == "hybride")
check("'Elektrisch' → electrique", canon_fuel("Elektrisch") == "electrique")
check("'Overige brandstoffen' → inconnu", canon_fuel("Overige brandstoffen") is None)

v_nl = normalize_vehicle("BMW 116I/2006", "Airco", 2006, "Benzine", "Manueel")
v_fr = normalize_vehicle("BMW 116i essence", "Clim", 2006, "Essence", "Manuelle")
print(f"     {v_nl.key()}\n     {v_fr.key()}")
check("la même voiture décrite en NL et en FR donne UNE clé",
      v_nl.key() == v_fr.key())


# ── 10. Identification du véhicule ─────────────────────────
print("\n[10] IDENTIFICATION DU VÉHICULE")
check("'BMW serie' seul → inexploitable",
      not vehicle_usable(normalize_vehicle("BMW serie", "", 2015)))
check("'Mercedes classe' seul → inexploitable",
      not vehicle_usable(normalize_vehicle("Mercedes classe", "", 2015)))
# La propriété testée est inchangée — les deux écritures doivent converger.
# Seule la valeur commune a changé : "320" isolait ces annonces de
# `bmw|3-reeks` (le nom du site), elles n'avaient donc aucun comparable.
check("'Serie 320d' et '320d' convergent, désormais vers la série",
      normalize_vehicle("Bmw SERIE 320d", "", 2015).model
      == normalize_vehicle("BMW 320d", "", 2015).model == "3-reeks")
check("'Classe E220D' et 'E220 CDI' convergent",
      normalize_vehicle("Mercedes Classe E220D", "", 2015).model
      == normalize_vehicle("Mercedes E220 CDI", "", 2015).model == "e220")
check("Série 1 et Série 5 ne se mélangent pas",
      normalize_vehicle("BMW serie 1", "", 2015).model
      != normalize_vehicle("BMW serie 5 520d", "", 2015).model)

# "van" = "de" en néerlandais : jamais un utilitaire
v_van = normalize_vehicle("Volkswagen Golf 7 1.2 TSI",
                          "mooie golf van eerste eigenaar, airco", 2015)
print(f"     Golf 'van eerste eigenaar' → carrosserie = {v_van.body}")
check("'van' néerlandais ne fait pas un utilitaire", v_van.body != "utilitaire")
check("'bestelwagen' reste un utilitaire",
      normalize_vehicle("Renault Kangoo bestelwagen", "", 2015).body == "utilitaire")


# ── 11. Le pool de comparables ─────────────────────────────
print("\n[11] POOL DE COMPARABLES")
base_pool = [{"price_eur": 9000 + i * 120, "mileage_km": 120000 + i * 900,
              "year": 2015, "vkey": "opel|corsa|essence|manuelle",
              "has_defect": False, "seller_type": "particulier"}
             for i in range(14)]
cible = {"year": 2015, "mileage_km": 122000, "vkey": "opel|corsa|essence|manuelle"}

# `pmin` = moyenne des 3 prix les plus bas. Si la cible entre dans son
# propre pool, elle tire son plancher vers le bas et fabrique de la marge.
# (Prix volontairement plausible : à 3 000 € le filtre MAD l'écarterait et
# le test ne prouverait rien.)
soi_meme = {**base_pool[0], "price_eur": 8400}
val_sans = value_market(cible, base_pool)
val_avec = value_market(cible, base_pool + [soi_meme])
print(f"     pmin sans la cible : {val_sans.pmin} € · "
      f"si elle s'auto-comparait à 8 400 € : {val_avec.pmin} €")
check("une annonce bon marché tire bien le plancher — d'où l'exclusion",
      val_avec.pmin < val_sans.pmin)

import run as runmod
import carsniper.notify as notify_mod
import inspect
sig = inspect.signature(runmod._pool)
check("run._pool exige l'identifiant à exclure", "exclure_id" in sig.parameters)
_cp0 = _dbm.init(":memory:")
_cp0.execute("INSERT INTO listings(source_id,external_id,title,price_eur,year,"
             "mileage_km,vkey_loose,status,seller_type) VALUES(1,'p1','Golf',"
             "5000,2015,120000,'volkswagen|golf','active','particulier')")
_cp0.execute("INSERT INTO listings(source_id,external_id,title,price_eur,year,"
             "mileage_km,vkey_loose,status,seller_type) VALUES(1,'p2','Golf',"
             "6000,2015,120000,'volkswagen|golf','active','particulier')")
_cp0.commit()
_pid = _cp0.execute("SELECT id FROM listings WHERE external_id='p1'").fetchone()["id"]
_pool0 = runmod._pool(_cp0, "volkswagen|golf", _pid)
check("run._pool exclut RÉELLEMENT la cible de son propre pool",
      len(_pool0) == 1 and _pool0[0]["price_eur"] == 6000)
_cp0.close()

# un comparable sans année n'est pas un comparable
sans_annee = [{**c, "year": None} for c in base_pool]
check("comparables sans année → refus d'évaluer",
      value_market(cible, sans_annee).method == "insufficient_data")
sans_km = [{**c, "mileage_km": None} for c in base_pool]
check("comparables sans kilométrage → refus d'évaluer",
      value_market(cible, sans_km).method == "insufficient_data")

# un pool jamais contrôlé pour défauts vaut moins qu'un pool vérifié
verifie = [{**c, "defauts_analyses": True} for c in base_pool]
inconnu = [{**c, "defauts_analyses": False} for c in base_pool]
cv = value_market(cible, verifie).confidence
ci = value_market(cible, inconnu).confidence
print(f"     confiance pool vérifié {cv} · pool non contrôlé {ci}")
check("un pool non contrôlé pour défauts inspire moins confiance", ci < cv)


# ── 12. Confiance : le cœur du problème ────────────────────
print("\n[12] CONFIANCE — refuser de se tromper avec assurance")
pool_aygo = [{"price_eur": 16000 + (i % 9) * 500, "mileage_km": 12000 + (i % 6) * 800,
              "year": 2024, "vkey": "toyota|aygo|essence|automatique|1.0|berline",
              "has_defect": False, "defauts_analyses": True,
              "seller_type": "particulier"} for i in range(20)]
cible_aygo = {"year": 2024, "mileage_km": 12000,
              "vkey": "toyota|aygo|essence|automatique|1.0|berline"}
val_aygo = value_market(cible_aygo, pool_aygo)

epave = {"title": "Toyota Aygo X 1.0 2025 schadewagen",
         "description": "Automaat, rijdt goed. Bel me.",
         "price_eur": 2500, "mileage_km": 12000, "year": 2024, "photo_count": 8}
veh_e = normalize_vehicle(epave["title"], epave["description"], 2024, "Benzine", "Automaat")
def_e = detect_defects(epave["title"] + " " + epave["description"], lexicon)
res_e = compute_deal(epave, veh_e, def_e, val_aygo, len(pool_aygo), 0.5, 0, None, profile)
print(f"     épave 2 500 € vs marché {val_aygo.p50} € → score {res_e['deal_score']} "
      f"({res_e['tier']}), confiance {res_e['confidence']:.0%}")
for x in res_e["confidence_limites"]:
    print(f"       ! {x}")
check("l'épave est détectée comme accidentée",
      any(d.code == "accident" and not d.negated for d in def_e))
# Règle métier : un dommage ne retire JAMAIS l'annonce du radar. Elle peut
# être notifiée si le prix le justifie — c'est le mécanicien qui tranche.
# Mais elle ne doit pas monter en GREAT/SNIPER avec une fiabilité élevée.
check("l'épave n'est PAS un GREAT DEAL", res_e["tier"] not in ("great", "sniper"))
check("le défaut est visible dans le résultat",
      "accident" in [d["code"] for d in res_e["defauts_detail"] if not d["negated"]])
check("la fiabilité est abaissée par la décote inexpliquée",
      res_e["fiabilite"] < 0.80)
check("et la raison est écrite noir sur blanc",
      any("sous la moins chère" in x for x in res_e["confidence_limites"]))
check("aucun coût de réparation n'a été soustrait",
      res_e["ecart_eur"] == epave["price_eur"] - res_e["moins_chere"])

# même annonce SANS le mot révélateur : la décote inexpliquée doit suffire
muette = {**epave, "title": "Toyota Aygo X 1.0 2025 automaat"}
def_m = detect_defects(muette["title"] + " " + muette["description"], lexicon)
res_m = compute_deal(muette, normalize_vehicle(muette["title"], "", 2024, "Benzine", "Automaat"),
                     def_m, val_aygo, len(pool_aygo), 0.5, 0, None, profile)
print(f"     même voiture sans le mot 'schadewagen' → score {res_m['deal_score']}, "
      f"confiance {res_m['confidence']:.0%}")
check("un prix inexplicablement bas ne produit pas d'alerte de haut rang",
      res_m["tier"] in ("below", "watch"))
check("et la fiabilité s'effondre faute d'explication",
      res_m["fiabilite"] <= 0.60)
# RÈGLE MÉTIER : un défaut déclaré ne peut JAMAIS améliorer le score.
# L'ancienne version atténuait la pénalité de décote inexpliquée quand un
# défaut « expliquait » le prix bas : le défaut faisait alors gagner 15 à
# 17 points et pouvait faire franchir le seuil. La pénalité est désormais
# la même dans les deux cas.
check("une annonce muette n'est PAS moins fiable qu'une annonce qui "
      "s'explique — le défaut ne pèse plus dans la fiabilité",
      res_m["fiabilite"] == res_e["fiabilite"])
check("et leurs scores sont donc identiques",
      res_m["deal_score"] == res_e["deal_score"])

# véhicule mal identifié → confiance plafonnée
flou = Valuation(pmin=9000, p25=9500, p50=10000, p75=10500, n=15,
                 method="weighted_median", confidence=0.9)
flou.pool_verifie, flou.iqr_ratio = 1.0, 0.1
veh_flou = normalize_vehicle("Auto te koop", "", 2015)
rep_vide = estimate_repairs([])
c_flou, r_flou = score_confidence({"price_eur": 9000, "year": 2015,
                                   "mileage_km": 100000}, veh_flou, [], flou, rep_vide)
c_net, _ = score_confidence({"price_eur": 9000, "year": 2015, "mileage_km": 100000},
                            normalize_vehicle("Volkswagen Golf 1.6 TDI", "", 2015,
                                              "Diesel", "Manuelle"),
                            [], flou, rep_vide)
print(f"     véhicule non identifié : {c_flou:.0%} · véhicule identifié : {c_net:.0%}")
check("un véhicule mal identifié reste sous l'exigence du segment budget",
      c_flou < 0.55)
check("nettement moins fiable qu'un véhicule bien identifié", c_flou < c_net - 0.2)
check("le plancher artificiel de 0.5 a disparu", c_flou < c_net)


# ── 13. Décision d'alerte ──────────────────────────────────
print("\n[13] DÉCISION D'ALERTE")
_pr_bas = {**profile, "notification_threshold": 10}
_pr_haut = {**profile, "notification_threshold": 99}
_vseuil = Valuation(pmin=5000, p25=5200, p50=5500, p75=5800, n=14, confidence=0.9)
_vseuil.niveau = "strict"; _vseuil.ancre_complete = True; _vseuil.flou_moyen = 0
_lseuil = {"price_eur": 5300, "description": "x" * 300, "photo_count": 8,
           "year": 2015, "mileage_km": 120000}
_vh = normalize_vehicle("Volkswagen Golf 1.4 TSI", "", 2015, "Essence", "Manuelle")
_rb = compute_deal(_lseuil, _vh, [], _vseuil, 14, 1, 0, None, _pr_bas)
_rh = compute_deal(_lseuil, _vh, [], _vseuil, 14, 1, 0, None, _pr_haut)
check("le seuil de la config change RÉELLEMENT la décision "
      f"(seuil 10 → {_rb['tier']}, seuil 99 → {_rh['tier']})",
      _rb["tier"] != "below" and _rh["tier"] == "below")

# une marge qui n'existe que grâce à la négociation ne monte pas haut
pool_c = [{"price_eur": 5600 + (i % 8) * 120, "mileage_km": 150000 + (i % 5) * 1000,
           "year": 2014, "vkey": "opel|corsa|essence|manuelle|1.2|berline",
           "has_defect": False, "defauts_analyses": True,
           "seller_type": "particulier"} for i in range(16)]
val_c = value_market({"year": 2014, "mileage_km": 150000,
                      "vkey": "opel|corsa|essence|manuelle|1.2|berline"}, pool_c)
juste = {"title": "Opel Corsa 1.2 essence", "description": "Voiture correcte, airco, 5 portes. Doit partir vite, demenagement.",
         "price_eur": val_c.pmin, "mileage_km": 150000, "year": 2014, "photo_count": 9}
res_j = compute_deal(juste, normalize_vehicle(juste["title"], "", 2014, "Essence", "Manuelle"),
                     detect_defects(juste["title"] + " " + juste["description"], lexicon),
                     val_c, len(pool_c), 50, 2, 3, profile)
print(f"     annonce AU PRIX de la moins chère → score {res_j['deal_score']} "
      f"(écart {res_j['ecart_pct']:+.0f} %)")
check("une annonce au prix de la moins chère marque très haut",
      res_j["score_prix"] == 100.0)
check("et déclenche une notification", res_j["tier"] != "below")

# véhicule pour pièces : jamais une opportunité
pieces = {**juste, "description": "Wordt verkocht voor onderdelen, sloopauto.",
          "price_eur": 1200}
res_p = compute_deal(pieces, normalize_vehicle(pieces["title"], "", 2014, "Essence", "Manuelle"),
                     detect_defects(pieces["title"] + " " + pieces["description"], lexicon),
                     val_c, len(pool_c), 5, 0, None, profile)
check("véhicule 'voor onderdelen' → aucune alerte", res_p["tier"] == "below")

# le cas métier qui DOIT passer : embrayage, défaut réel et chiffrable
bonne = {"title": "Opel Corsa 1.2 essence", "description":
         ("Voiture roulante, airco, 5 portes, entretiens faits. "
          "Koppeling versleten, moet vervangen worden. Vendue en l'etat, "
          "je n'ai pas le temps de la reparer."),
         "price_eur": 3200, "mileage_km": 150000, "year": 2014, "photo_count": 10}
res_b = compute_deal(bonne, normalize_vehicle(bonne["title"], "", 2014, "Essence", "Manuelle"),
                     detect_defects(bonne["title"] + " " + bonne["description"], lexicon),
                     val_c, len(pool_c), 30, 1, 5, profile)
print(f"     Corsa embrayage 3 200 € vs moins chère {val_c.pmin} € → "
      f"score {res_b['deal_score']} ({res_b['tier']}), écart {res_b['ecart_pct']:+.0f} %, "
      f"fiabilité {res_b['fiabilite']:.0%}")
check("un embrayage usé reste une OPPORTUNITÉ (pas de sur-filtrage)",
      res_b["tier"] != "below")
check("le défaut est affiché sans être soustrait du prix",
      res_b["repairs"]["items"] and res_b["ecart_eur"] == 3200 - val_c.pmin)
check("aucune réparation inventée sur les mots 'airco'/'5 portes'",
      {c for c, _, _ in res_b["repairs"]["items"]} == {"clutch"})


# ── 14. Chaîne Telegram de bout en bout ────────────────────
print("\n[14] TELEGRAM — envoi → clic → stockage → confirmation")
import io, json as _json, os as _os, urllib.parse as _up, sqlite3 as _sq
from carsniper import notify as _nf
from carsniper.storage import db as _db

_os.environ["TELEGRAM_TOKEN"] = "TEST"
_os.environ["TELEGRAM_CHAT_ID"] = "42"
APPELS = []
ETAT = {"updates": [], "sendMessage_ok": True}


class _Rep(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *a): return False


def _faux_urlopen(req, timeout=None):
    methode = req.full_url.rsplit("/", 1)[-1]
    corps = {k: v[0] for k, v in _up.parse_qs((req.data or b"").decode()).items()}
    APPELS.append((methode, corps))
    if methode == "sendMessage":
        if not ETAT["sendMessage_ok"]:
            raise OSError("Telegram injoignable")
        return _Rep(_json.dumps({"ok": True, "result": {"message_id": 777}}).encode())
    if methode == "getUpdates":
        return _Rep(_json.dumps({"ok": True, "result": ETAT["updates"]}).encode())
    return _Rep(_json.dumps({"ok": True, "result": True}).encode())


_vrai_urlopen = _nf.urllib.request.urlopen
_nf.urllib.request.urlopen = _faux_urlopen
try:
    chemin = _tmp("carsniper_test_feedback.db")
    if _os.path.exists(chemin):
        _os.remove(chemin)
    con = _db.init(chemin)
    con.execute("INSERT INTO listings(source_id,external_id,title,price_eur) "
                "VALUES(1,'x','Corsa',5000)")
    lid = con.execute("SELECT id FROM listings").fetchone()["id"]

    mid = _nf.send("alerte de test", "https://example.invalid/a")
    check("send() renvoie l'identifiant du message", mid == 777)
    boutons = _json.loads(APPELS[0][1]["reply_markup"])["inline_keyboard"]
    codes = [b.get("callback_data") for row in boutons for b in row if b.get("callback_data")]
    check("les 5 boutons de feedback partent avec l'alerte", len(codes) == 5)

    con.execute("INSERT INTO alerts(listing_id,tier,deal_score,trigger_reason,"
                "telegram_message_id) VALUES(?,?,?,?,?)", (lid, "good", 80, "new", mid))
    con.commit()

    ETAT["updates"] = [{"update_id": 10, "callback_query": {
        "id": "cb1", "data": "fb:good", "message": {"message_id": 777}}}]
    APPELS.clear()
    n = _nf.poll_feedback(con)
    stocke = con.execute("SELECT reaction FROM feedback").fetchall()
    confirmation = next((c for m, c in APPELS if m == "answerCallbackQuery"), {})
    check("le clic est enregistré", n == 1 and len(stocke) == 1
          and stocke[0]["reaction"] == "good")
    check("la confirmation dit bien 'enregistré'",
          "enregistr" in confirmation.get("text", ""))
    check("l'offset Telegram avance",
          con.execute("SELECT value FROM meta WHERE key='tg_offset'")
             .fetchone()["value"] == "10")

    # clic sur un message INCONNU : surtout ne pas mentir
    ETAT["updates"] = [{"update_id": 11, "callback_query": {
        "id": "cb2", "data": "fb:good", "message": {"message_id": 999}}}]
    APPELS.clear()
    n2 = _nf.poll_feedback(con)
    conf2 = next((c for m, c in APPELS if m == "answerCallbackQuery"), {})
    check("un message inconnu n'invente pas d'enregistrement", n2 == 0)
    check("et le dit clairement au lieu d'afficher 'enregistré'",
          "NON enregistr" in conf2.get("text", ""))

    # double clic : pas de doublon
    ETAT["updates"] = [{"update_id": 12, "callback_query": {
        "id": "cb3", "data": "fb:good", "message": {"message_id": 777}}}]
    _nf.poll_feedback(con)
    check("un double clic ne crée pas de doublon",
          con.execute("SELECT COUNT(*) FROM feedback").fetchone()[0] == 1)

    # l'anti-spam lit bien la réaction
    con.execute("INSERT INTO feedback(alert_id,listing_id,reaction) "
                "VALUES(1,?,'not_interested')", (lid,))
    con.commit()
    go, _ = _nf.should_notify(con, lid, 90, "great", 5000,
                              profile["antispam"])
    check("un ❌ éteint bien les alertes suivantes", go is False)

    # ── échec d'envoi : aucune alerte fantôme ──
    ETAT["sendMessage_ok"] = False
    mid_ko = _nf.send("alerte qui échoue", "https://example.invalid/b")
    check("send() renvoie None quand Telegram échoue", mid_ko is None)
    check("telegram_configure() distingue panne et absence de config",
          _nf.telegram_configure() is True)
    # Vérifié sur le COMPORTEMENT, pas sur le texte du code : une ligne dans
    # `alerts` signifie "reçu sur le téléphone". Si Telegram échoue, rien ne
    # doit être enregistré, sinon l'anti-spam bloque 72 h une annonce que tu
    # n'as jamais vue.
    _n_av = con.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
    _lid2 = con.execute(
        "INSERT INTO listings(source_id, external_id, title, price_eur, year, "
        "status, seller_type, url) VALUES(?,?,?,?,?,'active','particulier',?)",
        (1, "echec-1", "Opel Corsa 1.2 essence", 4000, 2014,
         "https://example.invalid/echec")).lastrowid
    con.commit()
    _res_ko = {"tier": "great", "deal_score": 88.0, "valuation": Valuation(),
               "fiabilite": 0.9, "explanation": [], "defauts_detail": []}
    ETAT["sendMessage_ok"] = False
    _parti = runmod._notifier(con, _lid2, _res_ko)
    check("envoi échoué → aucune alerte enregistrée",
          _parti is False
          and con.execute("SELECT COUNT(*) FROM alerts").fetchone()[0] == _n_av)

    # L'alerte non délivrée doit RESTER dans la file, pas disparaître.
    check("l'alerte non délivrée est conservée dans la file",
          _nf.en_attente(con) == 1)

    # Et c'est la reprise de file qui la livre, pas un second _notifier :
    # rappeler _notifier ne doit surtout PAS créer une seconde intention.
    _redepot = runmod._notifier(con, _lid2, _res_ko)
    check("rappeler _notifier ne duplique pas l'intention",
          _redepot is False
          and con.execute("SELECT COUNT(*) FROM outbox").fetchone()[0] == 1)

    ETAT["sendMessage_ok"] = True
    _bilan = _nf.reprendre(con)
    check("la reprise de file délivre l'alerte en attente",
          _bilan["delivrees"] == 1
          and con.execute("SELECT COUNT(*) FROM alerts").fetchone()[0] == _n_av + 1)
    check("et la file est alors vide", _nf.en_attente(con) == 0)
    con.close()
finally:
    _nf.urllib.request.urlopen = _vrai_urlopen
    _os.environ.pop("TELEGRAM_TOKEN", None)
    _os.environ.pop("TELEGRAM_CHAT_ID", None)


# ── 15. Traçabilité ────────────────────────────────────────
print("\n[15] TRAÇABILITÉ")
_cv0 = _dbm.init(":memory:")
_cols_val = {r["name"] for r in _cv0.execute("PRAGMA table_info(valuations)")}
_cv0.close()
check("la colonne value_pmin existe et porte l'ancre",
      "value_pmin" in _cols_val)
check("les comparables utilisés sont conservés",
      len(val_aygo.comparables) > 0)
_cd0 = _dbm.init(":memory:")
_cols_dec = {r["name"] for r in _cd0.execute("PRAGMA table_info(decisions)")}
_cd0.close()
check("la table decisions porte les limites de fiabilité",
      "limites_json" in _cols_dec)
check("le résultat porte le détail des défauts",
      "defauts_detail" in res_b and len(res_b["defauts_detail"]) > 0)



# ═══════════════════════════════════════════════════════════
#  ÉTAPE 1 — LE RADAR DU JOUR
#  2ememain est simulé : on teste le comportement du radar,
#  pas la disponibilité du site.
# ═══════════════════════════════════════════════════════════
print("\n[16] RADAR — détection des nouvelles annonces")

import os as _os2, time as _t2, json as _j2
from carsniper.sources.twoememain import TweedehandsSource as _TS
from carsniper.storage import db as _db2

_ID = [2_437_000_000]          # compteur d'identifiants, croissant comme sur le site


def _annonce(prix=5000, titre="Volkswagen Golf 1.4 TSI", date="Vandaag", **kw):
    """Fabrique un payload 2ememain plausible."""
    _ID[0] += 17
    return {
        "itemId": f"m{_ID[0]}", "title": titre, "date": date,
        "categorySpecificDescription": kw.get("desc", "Voiture en bon etat, entretiens faits."),
        "priceInfo": {"priceCents": prix * 100, "priceType": "FIXED"},
        "vipUrl": f"/v/auto/{_ID[0]}",
        "location": {"cityName": kw.get("ville", "Kasterlee"),
                     "latitude": 51.24, "longitude": 4.94, "distanceMeters": -1000},
        "imageUrls": ["a", "b", "c", "d", "e"],
        "sellerInformation": {"sellerId": 1},
        "attributes": [{"key": "constructionYear", "value": str(kw.get("annee", 2015))},
                       {"key": "mileage", "value": str(kw.get("km", 140000))},
                       {"key": "fuel", "value": kw.get("fuel", "Benzine")},
                       {"key": "transmission", "value": "Handgeschakeld"},
                       {"key": "advertiser", "value": "Particulier"}],
    }


class _FauxSite(_TS):
    """2ememain simulé : un stock d'annonces, servi trié par date."""

    def __init__(self, stock=None, trie_par_date=True):
        super().__init__(delay=0)
        self.stock = list(stock or [])
        self.trie_par_date = trie_par_date
        self.requetes = []

    def publier(self, *annonces):
        self.stock.extend(annonces)

    def _get(self, params, retries=2):
        self.requetes.append(dict(params))
        lot = sorted(self.stock, key=lambda r: int(r["itemId"][1:]),
                     reverse=True) if self.trie_par_date else list(self.stock)
        off = int(params.get("offset", 0))
        lim = int(params.get("limit", 100))
        return {"listings": lot[off:off + lim], "totalResultCount": len(lot)}


# Connexions remises par `_base_neuve`, pour pouvoir les refermer.
# Sous Linux on peut supprimer un fichier encore ouvert ; sous Windows non,
# et la suite s'arretait sur PermissionError [WinError 32] des la section
# [16e] — c'est-a-dire avant les trois quarts des tests, y compris tous
# ceux des defaillances.
_BASES_OUVERTES = {}


def _base_neuve(chemin=None):
    chemin = chemin or _tmp("carsniper_radar.db")

    ancienne = _BASES_OUVERTES.pop(chemin, None)
    if ancienne is not None:
        try:
            ancienne.close()
        except Exception:
            pass

    for cible in (chemin, chemin + "-wal", chemin + "-shm"):
        if not _os2.path.exists(cible):
            continue
        try:
            _os2.remove(cible)
        except PermissionError:
            # Un autre handle tient encore le fichier : plutot que d'echouer,
            # on travaille sur un nom neuf. Le test reste valide, seul le
            # fichier temporaire change.
            base, ext = _os2.path.splitext(chemin)
            chemin = f"{base}-{_os2.getpid()}-{len(_BASES_OUVERTES)}{ext}"
            break

    c = _db2.init(chemin)
    _db2.load_defects(c, lexicon)
    _BASES_OUVERTES[chemin] = c
    return c


# ── 16a. l'amorçage n'alerte pas, mais enregistre tout ─────
con = _base_neuve()
# 24 annonces, pas 12 : sous 20 identifiants, la mesure du tri n'a plus
# de valeur statistique (une suite descendante longue arrive par hasard) et
# le détecteur refuse de conclure. Le site en renvoie 100 par page.
site = _FauxSite([_annonce(prix=4000 + i * 50) for i in range(24)])
envois = []
_vrai_send = runmod.notify.envoyer_strict
runmod.notify.envoyer_strict = lambda msg, url=None: (envois.append(msg), 1)[1]
try:
    raws, diag = runmod._collecte_du_jour(con, site, verbose=False)
    check("l'amorçage lit bien tout le flux du jour", len(raws) == 24)
    check("le tri par date est reconnu", diag["tri_date"] is True)
    seen, new = runmod._ingest(con, site, raws, "amorcage",
                               seller_known="particulier", alerter=False)
    check("les 24 annonces sont enregistrées", new == 24)
    check("l'amorçage n'envoie AUCUNE alerte", len(envois) == 0)
    runmod._set_watermark(con, diag["filigrane_apres"], "fast")
    con.commit()
    filigrane1 = runmod._watermark(con, "fast")
    check("le filigrane est posé", filigrane1 > 0)

    # ── 16b. rien de neuf → aucune relecture inutile, aucune alerte ──
    site.requetes.clear()
    raws2, diag2 = runmod._collecte_du_jour(con, site, verbose=False)
    nouveaux = [r for r in raws2 if runmod._numid(r["itemId"]) > filigrane1]
    check("un cycle sans nouveauté ne trouve aucune annonce nouvelle",
          len(nouveaux) == 0)
    check("il s'arrête au filigrane, sans lire tout le flux",
          diag2["arret"] == "filigrane atteint" or diag2["pages"] <= 1)
    seen2, new2 = runmod._ingest(con, site, raws2, "fast_loop",
                                 seller_known="particulier")
    check("aucune annonce déjà vue n'est réenregistrée", new2 == 0)
    check("aucune 2e alerte sur les annonces déjà connues", len(envois) == 0)

    # ── 16c. une nouvelle annonce est captée et analysée ──
    site.publier(_annonce(prix=2600, titre="Volkswagen Golf 1.4 TSI",
                          desc="Vends rapidement, voiture en bon etat."))
    raws3, diag3 = runmod._collecte_du_jour(con, site, verbose=False)
    nouveaux3 = [r for r in raws3 if runmod._numid(r["itemId"]) > filigrane1]
    check("la nouvelle annonce est détectée au cycle suivant", len(nouveaux3) == 1)
    seen3, new3 = runmod._ingest(con, site, raws3, "fast_loop",
                                 seller_known="particulier")
    check("elle est enregistrée comme nouvelle", new3 == 1)
    runmod._set_watermark(con, diag3["filigrane_apres"], "fast")
    con.commit()
    check("le filigrane a avancé", runmod._watermark(con, "fast") > filigrane1)

    # ── 16d. la même annonce au cycle d'après : pas de 2e alerte ──
    avant = len(envois)
    raws4, _ = runmod._collecte_du_jour(con, site, verbose=False)
    runmod._ingest(con, site, raws4, "fast_loop", seller_known="particulier")
    check("l'annonce retrouvée au scan suivant ne réalerte pas",
          len(envois) == avant)
finally:
    runmod.notify.envoyer_strict = _vrai_send


# ── 16e. une annonce ancienne remontée ne doit rien faire rater ──
# Le site remonte parfois une vieille annonce (mise en avant, republication).
# Prendre le MINIMUM de la page pour décider l'arrêt faisait stopper dès la
# première rencontrée, et les pages suivantes — pleines de nouveautés —
# n'étaient jamais lues.
print("\n[16e] RADAR — annonce ancienne remontée par le site")
_F = 2_437_000_000


class _SiteOrdonne(_TS):
    """Sert les annonces dans un ordre imposé, pour reproduire un vrai flux."""

    def __init__(self, ordre):
        super().__init__(delay=0)
        self.ordre = ordre

    def _get(self, params, retries=2):
        o = int(params.get("offset", 0))
        l = int(params.get("limit", 100))
        return {"listings": self.ordre[o:o + l], "totalResultCount": len(self.ordre)}


def _ann_id(i):
    a = _annonce()
    a["itemId"] = f"m{i}"
    return a


_recentes = [_ann_id(_F + 1000 - i) for i in range(140)]
_ancienne = _ann_id(_F - 500_000)

for _nom, _ordre, _attendu in [
    ("une ancienne au milieu de la page", _recentes[:50] + [_ancienne] + _recentes[50:], 140),
    ("une ancienne en fin de page", _recentes[:99] + [_ancienne] + _recentes[99:], 140),
    ("plusieurs anciennes éparpillées",
     _recentes[:20] + [_ancienne] + _recentes[20:60] + [_ann_id(_F - 9)] + _recentes[60:], 140),
]:
    con = _base_neuve(_tmp("carsniper_remontee.db"))
    runmod._set_watermark(con, _F, "fast")
    con.commit()
    raws, diag = runmod._collecte_du_jour(con, _SiteOrdonne(_ordre), verbose=False)
    neufs = len([r for r in raws if runmod._numid(r["itemId"]) > _F])
    check(f"{_nom} → aucune nouveauté ratée ({neufs}/{_attendu})", neufs == _attendu)

# la vraie frontière est bien détectée, elle
con = _base_neuve(_tmp("carsniper_frontiere.db"))
runmod._set_watermark(con, _F, "fast")
con.commit()
_flux = [_ann_id(_F + 50 - i) for i in range(50)] + [_ann_id(_F - i) for i in range(200)]
raws, diag = runmod._collecte_du_jour(con, _SiteOrdonne(_flux), verbose=False)
neufs = len([r for r in raws if runmod._numid(r["itemId"]) > _F])
print(f"     frontière réelle : {diag['pages']} page(s) lues sur 250 annonces")
check("la vraie frontière arrête bien la pagination", diag["pages"] <= 3)
check("et les 50 nouveautés sont toutes captées", neufs == 50)
check("une page de sécurité est lue au-delà", diag["securite"] is True)


# ── 17. la vraie date de publication ────────────────────────
print("\n[17] DATE DE PUBLICATION — publiée aujourd'hui ≠ vue aujourd'hui")
con = _base_neuve(_tmp("carsniper_dates.db"))
site = _FauxSite([
    _annonce(prix=5000, titre="Volkswagen Golf 1.4 TSI", date="Vandaag"),
    _annonce(prix=5100, titre="Volkswagen Polo 1.2 TSI", date="Gisteren"),
    _annonce(prix=5200, titre="Opel Corsa 1.2 essence", date="24 aug 26"),
])
raws, _ = runmod._collecte_du_jour(con, site, verbose=False)
runmod._ingest(con, site, raws, "fast_loop", seller_known="particulier")
from datetime import date as _d, timedelta as _td
auj, hier = _d.today().isoformat(), (_d.today() - _td(days=1)).isoformat()
dates = {r["title"]: r["published_at"]
         for r in con.execute("SELECT title, published_at FROM listings")}
print(f"     {dates}")
check("'Vandaag' → aujourd'hui",
      dates.get("Volkswagen Golf 1.4 TSI") == auj)
check("'Gisteren' → HIER, plus estampillée aujourd'hui",
      dates.get("Volkswagen Polo 1.2 TSI") == hier)
check("une date explicite est respectée",
      dates.get("Opel Corsa 1.2 essence") not in (auj, None))
check("une annonce d'hier n'est pas une annonce du jour",
      len([v for v in dates.values() if v == auj]) == 1)

# la fraîcheur commande bien l'alerte
p_frais = dict(profile["profile"])
lst_hier = {"published_at": hier, "first_seen_at": None}
lst_auj = {"published_at": auj, "first_seen_at": None}
check("_est_frais accepte l'annonce du jour", runmod._est_frais(lst_auj, p_frais))
check("_est_frais refuse celle d'hier", not runmod._est_frais(lst_hier, p_frais))


# ── 18. robustesse du radar ─────────────────────────────────
print("\n[18] RADAR — robustesse")

# flux NON trié par date : on ne doit pas s'arrêter au filigrane
con = _base_neuve(_tmp("carsniper_ordre.db"))
melange = [_annonce(prix=4000 + i * 50) for i in range(30)]
import random as _rnd
_rnd.Random(1).shuffle(melange)
site_melange = _FauxSite(melange, trie_par_date=False)
raws, diag = runmod._collecte_du_jour(con, site_melange, verbose=False)
check("un flux non trié par date est reconnu comme tel", diag["tri_date"] is False)
check("dans ce cas on lit tout le flux (rien n'est raté)", len(raws) == 30)

# le filigrane n'avance pas si l'ingestion échoue
con = _base_neuve(_tmp("carsniper_filigrane.db"))
site = _FauxSite([_annonce(prix=5000) for _ in range(5)])
avant = runmod._watermark(con, "fast")
raws, diag = runmod._collecte_du_jour(con, site, verbose=False)
check("le filigrane reste inchangé tant qu'on ne l'écrit pas",
      runmod._watermark(con, "fast") == avant)
check("le diagnostic propose bien un filigrane à jour",
      diag["filigrane_apres"] > avant)

# la commande fast accepte --once et rend la main
import inspect as _ins
sig = _ins.signature(runmod.cmd_fast)
check("cmd_fast a un mode --once", "once" in sig.parameters)
check("cmd_fast boucle par défaut", sig.parameters["once"].default is False)
check("la cadence est bien déclarée dans la configuration",
      isinstance(runmod.COLL.get("fast_loop_seconds"), (int, float))
      and runmod.COLL["fast_loop_seconds"] > 0)
_sig_loop = _ins.signature(runmod.cmd_loop)
check("cmd_loop ne prend aucun argument obligatoire",
      not [p for p in _sig_loop.parameters.values()
           if p.default is p.empty])

# une passe unique se termine réellement
con = _base_neuve(_tmp("carsniper_once.db"))
_vrai_init = runmod.db.init
runmod.db.init = lambda *a, **k: con
_vrai_source = runmod._source
runmod._source = lambda: _FauxSite([_annonce(prix=5000 + i * 40) for i in range(6)])
_vrai_send = runmod.notify.envoyer_strict
runmod.notify.envoyer_strict = lambda msg, url=None: 1
try:
    t0 = _t2.time()
    runmod.cmd_fast(once=True)
    check("`fast --once` rend la main (pas de boucle)", _t2.time() - t0 < 20)
    check("la passe a bien enregistré les annonces",
          con.execute("SELECT COUNT(*) FROM listings").fetchone()[0] == 6)
    check("le filigrane est posé après la passe", runmod._watermark(con, "fast") > 0)

    # ── le filigrane n'avance QUE si l'ingestion a réussi ──
    # Sinon une erreur au milieu d'un cycle ferait sauter définitivement
    # toutes les annonces de ce cycle : elles ne seraient jamais relues.
    _fili_avant = runmod._watermark(con, "fast")
    _n_avant = con.execute("SELECT COUNT(*) FROM listings").fetchone()[0]
    runmod._source = lambda: _FauxSite([_annonce(prix=9000 + i * 40)
                                        for i in range(4)])
    _vrai_ingest = runmod._ingest
    runmod._ingest = lambda *a, **k: (_ for _ in ()).throw(
        RuntimeError("coupure réseau en pleine ingestion"))
    try:
        runmod.cmd_fast(once=True)          # l'erreur est attrapée, pas fatale
    finally:
        runmod._ingest = _vrai_ingest
    check("une ingestion qui échoue ne fait PAS avancer le filigrane",
          runmod._watermark(con, "fast") == _fili_avant)
    check("et n'enregistre aucune annonce à moitié",
          con.execute("SELECT COUNT(*) FROM listings").fetchone()[0] == _n_avant)

    # le cycle suivant, lui, rattrape bien ces annonces
    runmod.cmd_fast(once=True)
    check("le cycle suivant rattrape les annonces du cycle échoué",
          con.execute("SELECT COUNT(*) FROM listings").fetchone()[0] == _n_avant + 4)
    check("et le filigrane avance alors", runmod._watermark(con, "fast") > _fili_avant)
finally:
    runmod.db.init = _vrai_init
    runmod._source = _vrai_source
    runmod.notify.envoyer_strict = _vrai_send




def _compat_ok(a, b):
    """Les deux clés sont-elles comparables au sens du moteur ?"""
    from carsniper.engine import _compat
    return _compat(a, b)[0]


# ═══════════════════════════════════════════════════════════
#  ÉTAPE 2 — IDENTIFICATION DU VÉHICULE
# ═══════════════════════════════════════════════════════════
print("\n[19] IDENTIFICATION — les données du site priment sur la devinette")

from carsniper.engine import canon_body, MODEL_BRAND

# le modèle déclaré par 2ememain est utilisé en priorité
v = normalize_vehicle("Land Rover Range Rover Evoque 2.0 TD4", "", 2016,
                      "Diesel", "Automaat",
                      site_model="Range Rover Evoque", site_body="SUV of Terreinwagen")
print(f"     {v.key()}  [modèle: {v.model_source}, carrosserie: {v.body_source}]")
check("le modèle déclaré par le site est retenu", v.model_source == "site")
check("la carrosserie déclarée par le site est retenue", v.body_source == "site")
check("'SUV of Terreinwagen' devient 'suv'", v.body == "suv")

# le fourre-tout du site n'est PAS un modèle
v = normalize_vehicle("Peugeot 208 1.2 essence", "", 2015, "Benzine", "Manueel",
                      site_model="Overige modellen", site_body="Overige carrosserie")
check("'Overige modellen' n'est pas pris pour un modèle", v.model == "208")
check("'Overige carrosserie' n'est pas prise pour une carrosserie", v.body is None)

# un titre sans marque reste exploitable grâce au modèle déclaré
for titre, modele, attendu in [
    ("GOLF 5 UNITED 1.4 ESSENCE", "Golf", "volkswagen"),
    ("Touran 7-zits benzine", "Touran", "volkswagen"),
    ("GLC 250 4matic automaat", "GLC", "mercedes"),
    ("3 reeks 320d", "3 reeks", "bmw"),
]:
    v = normalize_vehicle(titre, "", 2016, "Diesel", "Automaat", site_model=modele)
    check(f"'{titre[:26]}' → marque retrouvée ({attendu})",
          v.make == attendu and vehicle_usable(v))

# BMW Série 1 et Série 3 restent séparées
v1 = normalize_vehicle("1 reeks 116d", "", 2016, "Diesel", "Manueel", site_model="1 reeks")
v3 = normalize_vehicle("3 reeks 320d", "", 2016, "Diesel", "Manueel", site_model="3 reeks")
print(f"     {v1.key()}\n     {v3.key()}")
check("BMW Série 1 ≠ BMW Série 3", v1.model != v3.model)
check("et leurs clés sont incompatibles", not _compat_ok(v1.key(), v3.key()))

# la carrosserie du site sépare ce que les mots-clés mélangeaient
berline = normalize_vehicle("Toyota Yaris 1.5 Hybrid", "", 2022, "Hybride",
                            "Automaat", site_model="Yaris", site_body="Stadsauto")
suv = normalize_vehicle("Toyota Yaris Cross 1.5 Hybrid", "", 2022, "Hybride",
                        "Automaat", site_model="Yaris Cross", site_body="SUV of Terreinwagen")
check("une Yaris et une Yaris Cross ne sont plus comparables",
      not _compat_ok(berline.key(), suv.key()))

# "van" néerlandais : toujours neutralisé, et le site tranche
v = normalize_vehicle("Volkswagen Golf 7 1.2 TSI",
                      "mooie golf van eerste eigenaar, airco", 2015,
                      "Benzine", "Handgeschakeld", site_body="Stadsauto")
check("'van' néerlandais ne fait toujours pas un utilitaire", v.body != "utilitaire")
check("et la carrosserie vient du site", v.body == "berline")

# marques ajoutées
print("\n[20] MARQUES — celles qui manquaient")
for titre, marque in [("MG ZS 1.5 Luxury", "mg"), ("Rover 75 2.0 CDT", "rover"),
                      ("Saab 9-3 Aero Cabrio", "saab"), ("Chevrolet Aveo 1.2", "chevrolet"),
                      ("SsangYong Tivoli 1.6", "ssangyong"), ("Iveco Daily 35S12", "iveco"),
                      ("Lancia Ypsilon 1.2", "lancia")]:
    v = normalize_vehicle(titre, "", 2015, "Diesel", "Manuelle")
    check(f"{titre[:24]:<26} → {marque}", v.make == marque)
for faute, marque in [("Mercedez benz GLC 220", "mercedes"), ("peugoet 207 1.4", "peugeot"),
                      ("Peugeut GT 208", "peugeot")]:
    v = normalize_vehicle(faute, "", 2015, "Diesel", "Manuelle")
    check(f"faute de frappe '{faute[:20]}' → {marque}", v.make == marque)

check(f"table modèle→marque dérivée des données ({len(MODEL_BRAND)} entrées)",
      len(MODEL_BRAND) > 300 and MODEL_BRAND.get("golf") == "volkswagen")
check("carrosseries du site normalisées",
      canon_body("SUV of Terreinwagen") == "suv" and canon_body("Break") == "break"
      and canon_body("Overige carrosserie") is None)

# les champs sont bien captés par le parser et stockés
from carsniper.sources.twoememain import TweedehandsSource as _TS3
_p = _TS3().parse({"itemId": "m1", "title": "Test", "priceInfo": {"priceCents": 500000},
                   "location": {"cityName": "Gent", "latitude": 51.05, "longitude": 3.72,
                                "distanceMeters": -1000},
                   "attributes": [{"key": "model", "value": "Golf"},
                                  {"key": "body", "value": "Stadsauto"}]})
check("le parser capte site_model", _p["site_model"] == "Golf")
check("le parser capte site_body", _p["site_body"] == "Stadsauto")
check("le parser capte les coordonnées GPS",
      _p["latitude"] == 51.05 and _p["longitude"] == 3.72)
from carsniper.storage import db as _db3
check("site_model/site_body/latitude/longitude sont persistés",
      {"site_model", "site_body", "latitude", "longitude"} <= set(_db3.LISTING_COLS))



# ═══════════════════════════════════════════════════════════
#  ÉTAPE 3 — LES COMPARABLES
# ═══════════════════════════════════════════════════════════
print("\n[21] COMPARABLES — la vraie moins chère comme ancre")

from carsniper.engine import NIVEAUX, _aberrants_bas, _dedupliquer

_VK = "opel|corsa|essence|manuelle|1.2|berline"


def _pool(prix, cle_speciale=None, idx=0):
    out = []
    for i, p in enumerate(prix):
        out.append({"title": f"Corsa {i}", "price_eur": p,
                    "mileage_km": 140000 + i * 500, "year": 2014,
                    "vkey": cle_speciale if (cle_speciale and i == idx) else _VK,
                    "has_defect": False, "defauts_analyses": True,
                    "seller_type": "particulier"})
    return out


_CIBLE = {"year": 2014, "mileage_km": 142000, "vkey": _VK}

v = value_market(_CIBLE, _pool([3500, 3900, 4100, 4300, 4500, 4700, 4900, 5100, 5300, 5500]))
print(f"     prix 3500…5500 → ancre {v.pmin} € · médiane {v.mediane} € · n={v.n}")
check("l'ancre est la VRAIE moins chère, pas la moyenne des 3", v.pmin == 3500)
check("la médiane est fournie à part", v.mediane == 4600)
check("le nombre de comparables est fourni", v.n == 10)

# aberrant bas : écarté ET signalé
v = value_market(_CIBLE, _pool([1900, 3500, 3900, 4100, 4300, 4500, 4700, 4900, 5100, 5300]))
print(f"     avec un 1900 € → ancre {v.pmin} €, exclus {v.exclus}")
check("une annonce aberrante ne devient pas l'ancre", v.pmin == 3500)
check("et elle est signalée, pas cachée", v.exclus == [1900])
v = value_market(_CIBLE, _pool([1000, 4800, 5000, 5000, 5100, 5200, 5200, 5300, 5400, 5500]))
check("un prix à 20 % de la médiane est écarté", v.exclus == [1000])
# mais un vrai bon prix n'est PAS écarté
v = value_market(_CIBLE, _pool([3200, 3500, 3900, 4100, 4300, 4500, 4700, 4900, 5100, 5300]))
check("un prix simplement bas reste l'ancre", v.pmin == 3200 and not v.exclus)

# doublons
_p = _pool([3500, 3900, 4100, 4300, 4500, 4700, 4900, 5100, 5300, 5500])
_p += [dict(_p[0]), dict(_p[0])]
v = value_market(_CIBLE, _p)
check("les republications sont dédupliquées", v.n == 10 and v.doublons == 2)
check("_dedupliquer garde une seule occurrence",
      _dedupliquer([{"title": "A", "price_eur": 1, "year": 2, "mileage_km": 3}] * 3)[1] == 2)

# ancre incomplète
v = value_market(_CIBLE, _pool([3100, 3500, 3900, 4100, 4300, 4500, 4700, 4900, 5100, 5300],
                               cle_speciale="opel|corsa|essence|None|?|berline"))
print(f"     moins chère brute {v.moins_chere_brute} € (config partielle) "
      f"→ ancre retenue {v.pmin} €")
check("une annonce très incomplète ne devient pas l'ancre", v.pmin == 3500)
check("mais la moins chère brute reste consultable", v.moins_chere_brute == 3100)
check("et le rattrapage est signalé", v.ancre_complete is False)

# paliers de tolérance
print("\n[22] COMPARABLES — élargissement progressif")
check("trois paliers définis", len(NIVEAUX) == 3)
check("la marque/modèle/carburant/boîte/carrosserie restent TOUJOURS exigés",
      all(set(n) == {"nom", "year", "km", "fiabilite"} for n in NIVEAUX))
check("l'année se resserre plus que le kilométrage (mesuré sur la base)",
      NIVEAUX[0]["year"] == 1 and NIVEAUX[0]["km"] == 0.30
      and NIVEAUX[2]["year"] == 3 and NIVEAUX[2]["km"] == 0.50)
check("chaque élargissement coûte de la fiabilité",
      NIVEAUX[0]["fiabilite"] > NIVEAUX[1]["fiabilite"] > NIVEAUX[2]["fiabilite"])

_p12 = [{"title": f"c{i}", "price_eur": 4000 + i * 100, "mileage_km": 140000,
         "year": 2014, "vkey": _VK, "has_defect": False,
         "defauts_analyses": True, "seller_type": "particulier"} for i in range(12)]
niveaux_vus = []
for annee in (2014, 2016, 2017):
    v = value_market({"year": annee, "mileage_km": 142000, "vkey": _VK}, _p12)
    niveaux_vus.append((v.niveau, v.confidence))
print(f"     cible 2014/2016/2017 vs comparables 2014 → {niveaux_vus}")
check("le palier utilisé est tracé", [n for n, _ in niveaux_vus] == ["strict", "elargi", "large"])
check("la confiance baisse à chaque élargissement",
      niveaux_vus[0][1] > niveaux_vus[1][1] > niveaux_vus[2][1])

# on n'élargit JAMAIS sur la configuration
autre_carburant = [{**c, "vkey": "opel|corsa|diesel|manuelle|1.2|berline"} for c in _p12]
check("un carburant différent n'est jamais accepté, même au palier large",
      value_market({"year": 2014, "mileage_km": 142000, "vkey": _VK},
                   autre_carburant).n == 0)
autre_carrosserie = [{**c, "vkey": "opel|corsa|essence|manuelle|1.2|break"} for c in _p12]
check("une carrosserie différente n'est jamais acceptée",
      value_market({"year": 2014, "mileage_km": 142000, "vkey": _VK},
                   autre_carrosserie).n == 0)

# les comparables utilisés restent consultables
v = value_market(_CIBLE, _pool([3500, 3900, 4100, 4300, 4500, 4700, 4900, 5100, 5300, 5500]))
check("les comparables retenus sont conservés pour l'explication",
      len(v.comparables) == 10 and v.comparables[0]["price_eur"] == 3500)
check("chaque comparable porte son degré d'incertitude",
      all("flous" in c for c in v.comparables))

# ═══════════════════════════════════════════════════════════
#  ÉTAPES 5 & 6 — DÉFAUT INFORMATIF, DISTANCE, MESSAGE
# ═══════════════════════════════════════════════════════════
print("\n[23] DÉFAUT — une information, jamais une pénalité financière")

_VKC = "opel|corsa|essence|manuelle|1.2|berline"


def _marche(mc, n=15):
    return [{"title": f"Corsa {i}", "price_eur": int(mc * (1 + 0.05 * i)),
             "mileage_km": 140000 + i * 700, "year": 2014, "vkey": _VKC,
             "has_defect": False, "defauts_analyses": True,
             "seller_type": "particulier"} for i in range(n)]


def _annonce_test(prix, desc, mc=5000):
    P = _marche(mc)
    v = value_market({"year": 2014, "mileage_km": 142000, "vkey": _VKC}, P)
    lst = {"title": "Opel Corsa 1.2 essence", "description": desc, "price_eur": prix,
           "mileage_km": 142000, "year": 2014, "photo_count": 10,
           "seller_type": "particulier", "fuel": "essence",
           "transmission": "manuelle", "location": "Gent",
           "latitude": 51.05, "longitude": 3.72, "vkey": _VKC}
    veh = normalize_vehicle(lst["title"], desc, 2014, "Essence", "Manuelle")
    hits = detect_defects(f"{lst['title']} {desc}", lexicon)
    return lst, v, compute_deal(lst, veh, hits, v, len(P), 0.3, 0, None, profile)

# le cas exact de la consigne : 4 000 € face à 5 000 €, embrayage HS
_l, _v, _saine = _annonce_test(4000, "Voiture en bon etat, airco, 5 portes.")
_l2, _v2, _defaut = _annonce_test(4000, "Koppeling versleten, moet vervangen worden.")
print(f"     saine  {_saine['deal_score']:.0f}/100   ·   embrayage HS "
      f"{_defaut['deal_score']:.0f}/100  (moins chère {_v.pmin} €)")
check("une annonce à 4 000 € face à 5 000 € est notifiée", _saine["tier"] != "below")
check("la MÊME annonce avec embrayage HS est notifiée aussi",
      _defaut["tier"] != "below")
check("le défaut ne change PAS le score de prix",
      _saine["score_prix"] == _defaut["score_prix"])
check("le défaut ne retire rien du prix",
      _saine["ecart_eur"] == _defaut["ecart_eur"])
check("mais il est bien détecté et disponible",
      "clutch" in [d["code"] for d in _defaut["defauts_detail"] if not d["negated"]])
check("aucun coût de réparation n'existe dans le résultat",
      not any(k in _defaut for k in
              ("true_deal_value", "true_cost_low", "margin_pct", "marge_affichee")))

# tous les types de défauts restent dans le radar
for desc, code in [("Motorschade, rijdt niet meer.", "engine"),
                   ("Versnellingsbak defect.", "gearbox"),
                   ("Airco kapot.", "aircon"),
                   ("Banden versleten.", "tyres"),
                   ("Accu defect.", "battery"),
                   ("Carrosserieschade aan de zijkant.", "accident"),
                   ("Remmen te vervangen.", "brakes")]:
    _, _, r = _annonce_test(4000, desc)
    detectes = [d["code"] for d in r["defauts_detail"] if not d["negated"]]
    check(f"{code:<10} détecté et l'annonce reste notifiable",
          code in detectes and r["tier"] != "below")

# le message nomme le défaut sans le chiffrer
_msg = notify_mod.format_alert(_l2, _defaut, 0, 0.3)
check("le message nomme le défaut en clair", "embrayage" in _msg)
check("le message ne chiffre AUCUN coût de réparation",
      "garage" not in _msg.lower() and "toi " not in _msg)


print("\n[24] DISTANCE — information, jamais un filtre du score")
from carsniper.engine import distance_km as _dist

check("Anderlecht → 0 km", _dist(50.8333, 4.3000, 50.8333, 4.3000) == 0.0)
check("Gent ≈ 47 km", 45 <= _dist(51.05, 3.72, 50.8333, 4.3000) <= 50)
check("Arlon ≈ 167 km", 160 <= _dist(49.68, 5.81, 50.8333, 4.3000) <= 175)
check("coordonnées absentes → distance inconnue",
      _dist(None, None, 50.8333, 4.3000) is None)
check("coordonnées (0,0) rejetées", _dist(0, 0, 50.8333, 4.3000) is None)

# la distance n'entre pas dans le score
_proche = dict(_l); _proche.update(latitude=50.84, longitude=4.31)
_loin = dict(_l); _loin.update(latitude=49.68, longitude=5.81)
_veh = normalize_vehicle(_l["title"], "", 2014, "Essence", "Manuelle")
_r_proche = compute_deal(_proche, _veh, [], _v, 15, 0.3, 0, None, profile)
_r_loin = compute_deal(_loin, _veh, [], _v, 15, 0.3, 0, None, profile)
check("une voiture à 167 km a EXACTEMENT le même score qu'à 1 km",
      _r_proche["deal_score"] == _r_loin["deal_score"])

_l["distance_km"] = _dist(51.05, 3.72, 50.8333, 4.3000)
_msg = notify_mod.format_alert(_l, _saine, 0, 0.3)
check("le message affiche la ville", "Gent" in _msg)
check("et la distance depuis Bruxelles", "Bruxelles" in _msg and "47" in _msg)
check("en précisant que c'est à vol d'oiseau", "vol d'oiseau" in _msg)
_sans = dict(_l); _sans["distance_km"] = None
check("distance inconnue → dit clairement, jamais inventée",
      "inconnue" in notify_mod.format_alert(_sans, _saine, 0, 0.3))


print("\n[25] MESSAGE — tout ce qu'il faut pour décider d'appeler")
_msg = notify_mod.format_alert(_l, _saine, 0, 0.3)
for quoi, motif in [("le prix demandé", "4 000 €"),
                    ("la moins chère comparable", "Moins chère comparable"),
                    ("l'écart en € et en %", "Écart"),
                    ("le nombre de comparables", "comparables"),
                    ("le score sur 100", "Score"),
                    ("la ville", "📍"),
                    ("la distance", "📏"),
                    ("la configuration comparée", "Même configuration")]:
    check(f"le message donne {quoi}", motif in _msg)
check("la médiane est présente comme information secondaire", "Médiane" in _msg)


print("\n[26] PANNE ÉNONCÉE vs ORGANE ENTRETENU — formulations réelles de la base")

def _codes(t):
    return [(h.code, h.negated) for h in detect_defects(t, lexicon)]

def _actif(t, code):
    return (code, False) in _codes(t)

def _nie(t, code):
    return (code, True) in _codes(t) or code not in [c for c, _ in _codes(t)]

# ── a) une panne ÉNONCÉE n'est jamais annulée par un mot d'entretien.
#    Ces phrases sont extraites telles quelles de la base réelle.
for texte, code in [
        ("zeer goed onderhouden maar carrosserieschade", "accident"),
        ("schadewagen, rijdt goed", "accident"),
        ("lichte schade carosserie rondom van vangrail interieur perfect onderhouden", "accident"),
        ("nieuwe batterij nieuw kleppendeksel carosserie heeft schade bumper en zijdeur", "accident"),
        ("129.000 km rijdt erg goed wat lichaamsschade te koop in de staat", "accident"),
        ("demarre et roule moteur ok boite ok details : accidente avant gauche", "accident"),
        ("suivi d'entretien distribution change degat carrosserie mais mecanique impeccable", "accident"),
        ("afgekeurd op olielek wagen rijd nog goed", "no_ct"),
        ("afgekeurd voor deurdrempel rijdt en schakelt perfect voor de rest", "no_ct"),
        ("nieuwe batterij de wagen is uitgerust met een trekhaak roest op geleiders schuifdeur", "corrosion"),
        ("bmw 116i 4 nieuwe banden rijdt nog motorprobleem", "engine"),
        ("start en rijd perfect kleine krasjes en deukjes zie foto", "cosmetic"),
        ("voor stukken of voor opmaak rijd nog perfect", "for_parts")]:
    check(f"{code:<9} énoncé, non annulé par l'entretien — « {texte[:38]}… »",
          _actif(texte, code))

# ── b) l'inverse : un ORGANE simplement entretenu ne devient pas une panne.
for texte, code in [
        ("nieuwe koppeling geplaatst", "clutch"),
        ("koppeling vervangen op 120000 km", "clutch"),
        ("distributieriem vervangen", "timing"),
        ("nieuwe banden voor en achter", "tyres"),
        ("remmen en schijven nieuw", "brakes"),
        ("airco recent bijgevuld", "aircon")]:
    check(f"{code:<9} entretenu, PAS compté en panne — « {texte[:38]} »",
          _nie(texte, code))

# ── c) rien ne doit se déclencher sur une annonce saine ordinaire.
for texte in ["golf 1.4 tsi in goede staat, onderhoudsboekje aanwezig",
              "airco aanwezig, cruise control, parkeersensoren",
              "eerste eigenaar, altijd goed onderhouden, gekeurd voor verkoop"]:
    check(f"annonce saine → aucun défaut — « {texte[:40]} »",
          not [c for c, n in _codes(texte) if not n])

# ── d) le champ « schade: » du site est un INTITULÉ, pas un dommage.
check("« schade: schadevrij » n'est pas un accident",
      not _actif("onderhouden volgens voorschriften: ja schade: schadevrij", "accident"))
check("« ongevalsvrij » n'est pas un accident",
      not _actif("wagen is als nieuw en ongevalsvrij abs", "accident"))
check("« ongevallenvrij » non plus",
      not _actif("ongevallenvrij, eerste eigenaar", "accident"))
check("« schadevri » tronqué par le site n'est pas un accident",
      not _actif("aantal eigenaren: 2 schadevri", "accident"))
check("« ongeval- en schadevrij » n'est pas un accident",
      not _actif("ongeval- en schadevrij wintervelgen inbegrepen", "accident"))
check("mais « ongevalsvoertuig » en est un",
      _actif("ongevalsvoertuig linksachter maar herstelbaar", "accident"))
check("mais « schade: bumper spatbord » reste un accident",
      _actif("start goed 2 sleutels airco schade : bumper spatbord velg", "accident"))
check("et « met ongeval gehad » aussi",
      _actif("auto met ongeval gehad in 2019", "accident"))

# ── e) une négation explicite prime toujours.
for texte, code in [("geen schade, ongevalsvrij", "accident"),
                    ("nooit ongeval gehad", "accident"),
                    ("aucun probleme de moteur", "engine")]:
    check(f"négation explicite respectée — « {texte} »", not _actif(texte, code))


print("\n[27] ORGANE vs MARQUEUR — le marqueur doit qualifier LE BON organe")

# Le piège : une seule proposition cite plusieurs organes et un seul mot
# de panne. Sans rattachement, ce mot contaminait tous les organes cités.
for texte, code, attendu in [
    # a) le marqueur vise un AUTRE organe de la même phrase
    ("opel corsa 1.0 turbo 115cv / airco / probleme joint de culasse", "headgasket", True),
    ("opel corsa 1.0 turbo 115cv / airco / probleme joint de culasse", "turbo", False),
    ("opel corsa 1.0 turbo 115cv / airco / probleme joint de culasse", "aircon", False),
    # b) le marqueur est trop loin : il parle d'autre chose
    ("fiat punto 220 000km airco euro 5 diesel start en rijdt demarre "
     "et roule entretien a prevoir", "aircon", False),
    # c) le signal le PLUS PROCHE est un entretien, pas une panne
    ("disques + plaquettes arriere recemment remplaces entretien a prevoir",
     "brakes", False),
    # d) énumération : le marqueur porte sur TOUS les organes coordonnés
    ("turbo en roetfilter te vervangen", "turbo", True),
    ("turbo en roetfilter te vervangen", "dpf_egr", True),
    ("remmen et pneus a changer", "brakes", True),
    ("remmen et pneus a changer", "tyres", True),
    # e) et surtout : les vraies pannes restent détectées
    ("airco werkt niet", "aircon", True),
    ("turbo casse", "turbo", True),
    ("probleme turbo", "turbo", True),
    ("draagarm te vervangen", "suspension", True),
    ("koppeling kabel defect", "clutch", True),
    ("le moteur tourne au demarreur mais ne demarre pas", "starter_alt", True),
    # f) l'équipement seul ne déclenche jamais rien
    ("golf 1.4 tsi airco cruise control parkeersensoren", "aircon", False),
    ("clio 5 esprit alpine 145 cv e-tech hybrid boite automatique", "gearbox", False),
    ("mg hs luxury 1.5 turbo 162ch", "turbo", False)]:
    obtenu = _actif(texte, code)
    check(f"{code:<11} {'=' if attendu else '≠'} panne — « {texte[:44]}… »",
          obtenu == attendu)

# « HS » est aussi un modèle MG et un nom de garage : 61 des 91 occurrences
# de la base ne sont PAS "hors service".
# Un TRAITEMENT contre un défaut n'est pas le défaut.
check("« anti corrosie » n'est pas de la corrosion",
      not _actif("gezandstraald en gecoat met anti corrosie", "corrosion"))
check("« behandeld tegen roest » non plus",
      not _actif("behandeld tegen roest", "corrosion"))
check("« beschermringen tegen stoepschade » n'est pas un accident",
      not _actif("beschermringen tegen stoepschade", "accident"))
check("mais « lichte roest onderaan » reste de la corrosion",
      _actif("lichte roest onderaan", "corrosion"))

check("« MG HS » n'est pas une panne", not _actif("mg hs 1.5 t-gdi luxury", "turbo"))
check("« HS Auto » non plus", not _actif("hs auto biedt u deze wagen aan", "engine"))
check("mais « joint de culasse hs » en est une",
      _actif("kia carens 1.7 crdi joint de culasse hs", "headgasket"))
check("et « 2 pneus hs » aussi", _actif("2 pneus hs tel 0495/577436", "tyres"))


print("\n[28] MÊME CONFIGURATION — deux gammes ne se mélangent jamais")

def _k(titre, annee=2016, carb=None, boite=None, site_model=None, site_body=None):
    return normalize_vehicle(titre, "", annee, carb, boite,
                             site_model=site_model, site_body=site_body).key()

def _melange(a, b, **kw):
    return _compat_ok(_k(a, **kw), _k(b, **kw))

for a, b in [("BMW Serie 1 118d", "BMW Serie 3 318d"),
             ("BMW 1 reeks 118i", "BMW 3 reeks 320i"),
             ("Mercedes Classe A 180", "Mercedes Classe B 180"),
             ("Mercedes Classe C 220", "Mercedes Classe E 220"),
             ("VW Golf 1.6 TDI", "VW Polo 1.6 TDI"),
             ("Peugeot 208 1.2", "Peugeot 2008 1.2"),
             ("Renault Clio 1.5 dci", "Renault Captur 1.5 dci"),
             ("Audi A3 1.6 tdi", "Audi A4 1.6 tdi"),
             ("Fiat 500 1.2", "Fiat 500L 1.2"),
             ("VW Golf 1.6 TDI", "VW Golf 1.4 TSI")]:
    check(f"{a} ≠ {b}", not _melange(a, b))

# Le site distingue Yaris et Yaris Cross, Golf et Golf Plus : la carrosserie
# et le modèle déclarés priment sur le titre.
check("Yaris ≠ Yaris Cross",
      not _compat_ok(_k("Toyota Yaris 1.5", site_model="Yaris", site_body="Berline"),
                     _k("Toyota Yaris Cross 1.5", site_model="Yaris Cross",
                        site_body="SUV")))
check("Golf ≠ Golf Plus",
      not _compat_ok(_k("VW Golf 1.4", site_model="Golf"),
                     _k("VW Golf Plus 1.4", site_model="Golf Plus")))
check("Aygo ≠ Aygo X",
      not _compat_ok(_k("Toyota Aygo 1.0", site_model="Aygo"),
                     _k("Toyota Aygo X 1.0", site_model="Aygo X")))

# Titre et site doivent produire la MÊME clé, sinon la même voiture ne se
# compare jamais à elle-même : "Classe A" (titre) = "A-Klasse" (site).
check("« Classe A » du titre = « A-Klasse » du site",
      _k("Mercedes Classe A 180") == _k("Mercedes 180", site_model="A-Klasse"))
check("« Serie 3 » du titre = « 3-reeks » du site",
      _k("BMW Serie 3 320d") == _k("BMW 320d", site_model="3-reeks"))

# Le fourre-tout du site n'est pas un modèle : mieux vaut renoncer que
# retenir une finition.
check("« Overige modellen » → véhicule non identifié",
      not vehicle_usable(normalize_vehicle(
          "Peugeot Overige modellen Allure 1.2", "", 2018, None, None)))
check("mais un vrai modèle reste identifié",
      vehicle_usable(normalize_vehicle("Peugeot 208 Allure 1.2", "", 2018,
                                       None, None)))

# Et la carrosserie sépare bien deux versions du même modèle.
check("Golf berline ≠ Golf break",
      not _compat_ok(_k("VW Golf 1.6 TDI", site_body="Berline"),
                     _k("VW Golf 1.6 TDI", site_body="Break")))


print("\n[29] REPUBLICATIONS — une voiture republiée = UNE alerte")

import sqlite3 as _sq3
from carsniper.storage import db as _dbm

_c = _dbm.init(":memory:")
_sid = _dbm.source_id(_c, "2ememain")


def _poser(ext, titre, prix, vkey="toyota|chr|hybride|automatique|1.8|suv",
           annee=2019):
    _c.execute(
        "INSERT INTO listings(source_id, external_id, title, price_eur, year, "
        "vkey, status, seller_type) VALUES(?,?,?,?,?,?,'active','particulier')",
        (_sid, ext, titre, prix, annee, vkey))
    return _c.execute("SELECT last_insert_rowid()").fetchone()[0]


_TITRE = "Toyota C-HR 1.8 CVT HSD TC C-LUB LHD"
_a = _poser("m1", _TITRE, 17900)
_b = _poser("m2", _TITRE, 17900)            # republication : autre id du site
_d = _poser("m3", _TITRE, 16500)            # même voiture, prix baissé
_e = _poser("m4", "Toyota Yaris 1.5 hybride", 17900,
            vkey="toyota|yaris|hybride|automatique|1.5|berline")

_anti = dict(profile["antispam"])

go1, _ = _nf.should_notify(_c, _a, 88, "great", 17900, _anti)
check("la première annonce est notifiée", go1 is True)

_c.execute("INSERT INTO alerts(listing_id, deal_score, tier, sent_at) "
           "VALUES(?,?,?,datetime('now'))", (_a, 88, "great"))
_c.commit()

go2, _ = _nf.should_notify(_c, _b, 88, "great", 17900, _anti)
check("la republication identique n'en déclenche PAS une seconde",
      go2 is False)

go3, _ = _nf.should_notify(_c, _d, 92, "sniper", 16500, _anti)
check("mais un prix différent reste une annonce à part", go3 is True)

go4, _ = _nf.should_notify(_c, _e, 88, "great", 17900, _anti)
check("et une autre voiture au même prix passe toujours", go4 is True)

_anti_off = dict(_anti, suppress_reposts=False)
go5, _ = _nf.should_notify(_c, _b, 88, "great", 17900, _anti_off)
check("le garde-fou est débrayable par la config", go5 is True)
_c.close()


print("\n[30] RECALCUL NOCTURNE — amorçage silencieux, puis AUCUN plafond")

# La règle : un quota de notifications ne doit exister nulle part. Le seul
# garde-fou légitime est l'amorçage — le tout premier passage note l'état
# de départ sans rien envoyer, exactement comme le filigrane du radar.
check("aucun plafond de notifications dans la configuration",
      "night_max_alerts" not in (Path(__file__).resolve().parent.parent
                                 / "config" / "profile.yaml").read_text())

_cn = _base_neuve(_tmp("carsniper_recalc.db"))
_sid_n = _dbm.source_id(_cn, "2ememain") if False else 1

# 40 annonces largement sous le marché : toutes méritent une notification.
_POOL = "toyota|aygo|essence|manuelle|1.0|berline"
for i in range(40):
    _cn.execute(
        "INSERT INTO listings(source_id, external_id, title, description, "
        "price_eur, year, mileage_km, vkey, vkey_loose, status, seller_type, "
        "fuel, transmission, published_at, url) "
        "VALUES(1,?,?,'',?,?,?,?,'toyota|aygo','active','particulier',"
        "'Essence','Manuelle',date('now','localtime'),?)",
        (f"n{i}", f"Toyota Aygo 1.0 essence lot {i}", 4000 + i, 2015,
         120000 + i * 100, _POOL, f"https://example.invalid/{i}"))
# 20 comparables nettement plus chers : les 40 sont donc des affaires.
for i in range(20):
    _cn.execute(
        "INSERT INTO listings(source_id, external_id, title, description, "
        "price_eur, year, mileage_km, vkey, vkey_loose, status, seller_type, "
        "fuel, transmission, enriched_at) "
        "VALUES(1,?,?,'',?,?,?,?,'toyota|aygo','active','particulier',"
        "'Essence','Manuelle',datetime('now'))",
        (f"c{i}", f"Toyota Aygo 1.0 essence comparable {i}", 6000 + i * 30,
         2015, 120000 + i * 90, _POOL))
_cn.commit()

_envois = []
_vrai_init2, _vrai_send2 = runmod.db.init, runmod.notify.envoyer_strict
runmod.db.init = lambda *a, **k: _cn
runmod.notify.envoyer_strict = lambda msg, url=None: (_envois.append(msg), 1)[1]
try:
    r1 = runmod._recalculer(_cn)
    check("l'amorçage recalcule bien toutes les annonces", r1["analysees"] == 60)
    check("l'amorçage n'envoie AUCUNE notification", len(_envois) == 0)
    check("il enregistre l'état de départ",
          _cn.execute("SELECT COUNT(*) FROM recalc_state").fetchone()[0] == 60)

    # Deuxième passage, rien n'a changé : rien ne doit repartir.
    r2 = runmod._recalculer(_cn)
    check("un second passage sans changement ne notifie rien",
          r2["envoyees"] == 0 and len(_envois) == 0)

    # Maintenant les 40 baissent de prix : les 40 doivent partir.
    # AUCUN plafond ne doit les tronquer à 10.
    _cn.execute("UPDATE listings SET price_eur = price_eur - 1200 "
                "WHERE external_id LIKE 'n%'")
    _cn.commit()
    _envois.clear()
    r3 = runmod._recalculer(_cn)
    check(f"les 40 baisses de prix sont TOUTES notifiées (reçu : {len(_envois)})",
          len(_envois) == 40)
    check("le compteur interne le confirme", r3["envoyees"] == 40)

    # Une baisse minuscule n'est pas un événement.
    _cn.execute("UPDATE listings SET price_eur = price_eur - 5 "
                "WHERE external_id LIKE 'n%'")
    _cn.commit()
    _envois.clear()
    runmod._recalculer(_cn)
    check("une baisse insignifiante ne redéclenche rien", len(_envois) == 0)
finally:
    runmod.db.init, runmod.notify.envoyer_strict = _vrai_init2, _vrai_send2
    _cn.close()


print("\n[31] BMW — le code chiffré désigne la série, MAIS seulement chez BMW")

def _kb(titre, site_model=None):
    return normalize_vehicle(titre, "", 2016, "Diesel", "Manuelle",
                             site_model=site_model).key()

# a) le premier chiffre EST la série : sûr chez BMW.
for titre, attendu in [("BMW 320d", "3-reeks"), ("BMW 116i", "1-reeks"),
                       ("BMW 520d", "5-reeks"), ("BMW 118d", "1-reeks"),
                       ("BMW 114 i", "1-reeks"), ("BMW 730d", "7-reeks"),
                       ("BMW 418d", "4-reeks"), ("BMW 116iA Automaat", "1-reeks"),
                       ("BMW Serie 3 320d", "3-reeks"),
                       ("BMW 1-serie 118i", "1-reeks"),
                       ("BMW 3 reeks 320d", "3-reeks")]:
    check(f"{titre:<24} → bmw|{attendu}", _kb(titre).split("|")[1] == attendu)

# b) titre et site doivent tomber sur LA MÊME clé, sinon la même voiture
#    ne se compare jamais à elle-même.
for titre, site in [("BMW 320d", "3 Reeks"), ("BMW 116i", "1 Reeks"),
                    ("BMW 520d", "5 Reeks"),
                    ("BMW 218i Active Tourer", "2 Reeks Active Tourer"),
                    ("BMW 220i Gran Coupe", "2 Reeks Gran Coupé")]:
    check(f"« {titre} » (titre) = « {site} » (site)",
          _kb(titre) == _kb(titre, site_model=site))

# c) les variantes que le site sépare RESTENT séparées : un 218i Active
#    Tourer (monospace) n'est pas un 220i coupé.
for a, b in [("BMW 320d", "BMW 118d"),
             ("BMW 218i Active Tourer", "BMW 220i"),
             ("BMW 320d", "BMW 320d Gran Turismo"),
             ("BMW 320d", "BMW X3 xDrive")]:
    check(f"{a} ≠ {b}", not _compat_ok(_kb(a), _kb(b)))

# d) les modèles à lettre ne sont pas touchés.
for titre, attendu in [("BMW X1 sDrive", "x1"), ("BMW M3 Competition", "m3"),
                       ("BMW Z4 2.0", "z4"), ("BMW i3 electrique", "i3")]:
    check(f"{titre:<24} reste bmw|{attendu}", _kb(titre).split("|")[1] == attendu)

# e) ET SURTOUT : la règle ne s'étend PAS à Mercedes. "180" ne dit pas
#    s'il s'agit d'une Classe A, B, C ou E — on ne suppose rien.
for titre in ["Mercedes 180 d", "Mercedes 220 CDI", "Mercedes 200 essence",
              "Mercedes 250 CDI"]:
    mod = normalize_vehicle(titre, "", 2016, None, None).key().split("|")[1]
    check(f"« {titre} » n'est rattaché à AUCUNE classe (reste « {mod} »)",
          "klasse" not in (mod or ""))
check("et Classe A ≠ Classe B reste vrai",
      not _compat_ok(_kb("Mercedes Classe A 180"), _kb("Mercedes Classe B 180")))

# f) une marque qui utilise aussi des nombres n'est pas affectée.
for titre, attendu in [("Peugeot 208 1.2", "208"), ("Audi A3 1.6", "a3"),
                       ("Volvo 240 GL", "240"), ("Fiat 500 1.2", "500")]:
    check(f"{titre:<20} reste « {attendu} »",
          normalize_vehicle(titre, "", 2016, None, None).key().split("|")[1] == attendu)


print("\n[32] PANNE RÉSEAU ≠ MARCHÉ CALME")

# Un site injoignable renvoie une page vide, exactement comme un flux
# épuisé. Les confondre faisait afficher « arrêt : flux épuisé » pendant
# qu'aucune annonce n'était surveillée — une fausse garantie.
class _SiteEnPanne(_TS):
    def _get(self, params, retries=2):
        self.derniere_erreur = "URLError: <urlopen error Tunnel 403>"
        return {}


class _SiteVide(_TS):
    def _get(self, params, retries=2):
        self.derniere_erreur = None
        return {"listings": []}


_cp = _base_neuve(_tmp("carsniper_panne.db"))
_, _dp = runmod._collecte_du_jour(_cp, _SiteEnPanne(), verbose=False)
_, _dv = runmod._collecte_du_jour(_cp, _SiteVide(), verbose=False)

check("un site injoignable est signalé comme un ÉCHEC DE LECTURE",
      "ECHEC DE LECTURE" in _dp["arret"])
check("et l'erreur exacte est remontée",
      "403" in (_dp["erreur_lecture"] or ""))
check("un vrai flux épuisé reste « flux epuise »",
      _dv["arret"] == "flux epuise" and _dv["erreur_lecture"] is None)
check("une panne ne fait pas avancer le filigrane",
      _dp["filigrane_apres"] <= _dp["filigrane_avant"]
      or _dp["filigrane_avant"] == 0)
_cp.close()


print("\n[33] RADAR DE BOUT EN BOUT — baisse de prix et absence de plafond")

# Le radar doit re-notifier une annonce dont le prix BAISSE, même si elle
# a déjà été alertée : c'est précisément l'événement à ne pas rater.
_cr = _base_neuve(_tmp("carsniper_baisse.db"))
_msgs = []
_vi, _vs, _vsrc = runmod.db.init, runmod.notify.envoyer_strict, runmod._source
runmod.db.init = lambda *a, **k: _cr
runmod.notify.envoyer_strict = lambda msg, url=None: (_msgs.append(msg), 55)[1]

# Un marché : 14 Golf comparables autour de 8 000 €, plus la cible à 5 200 €.
_site = _FauxSite([_annonce(prix=8000 + i * 60, km=140000 + i * 500)
                   for i in range(14)])
_cible = _annonce(prix=5200, km=141000)
_site.publier(_cible)
runmod._source = lambda: _site
try:
    runmod.cmd_fast(once=True, amorcage_alerte=True)   # amorçage AVEC alertes
    _n1 = len(_msgs)
    check(f"la bonne affaire est notifiée au premier passage ({_n1} message(s))",
          _n1 >= 1)

    _msgs.clear()
    runmod.cmd_fast(once=True)
    check("le cycle suivant ne la renotifie pas", len(_msgs) == 0)

    # Le vendeur baisse son prix de 900 € : l'événement doit repartir.
    _cible["priceInfo"]["priceCents"] = 4300 * 100
    _msgs.clear()
    runmod.cmd_fast(once=True)
    check("une baisse de prix significative EST notifiée",
          len(_msgs) == 1 and "4 300" in _msgs[0])

    # Une baisse dérisoire ne redéclenche rien.
    _cible["priceInfo"]["priceCents"] = 4290 * 100
    _msgs.clear()
    runmod.cmd_fast(once=True)
    check("une baisse dérisoire ne redéclenche rien", len(_msgs) == 0)

finally:
    runmod.db.init, runmod.notify.envoyer_strict, runmod._source = _vi, _vs, _vsrc
    _cr.close()


print("\n[34] AUCUN PLAFOND — 30 bonnes affaires d'un coup = 30 notifications")

# Base neuve et marché propre : la propriété testée est « aucun quota »,
# elle ne doit dépendre ni de la calibration de la courbe ni de l'ordre
# d'analyse.
_cq = _base_neuve(_tmp("carsniper_quota.db"))
_mq = []
_vi3, _vs3, _vsrc3 = runmod.db.init, runmod.notify.envoyer_strict, runmod._source
runmod.db.init = lambda *a, **k: _cq
runmod.notify.envoyer_strict = lambda msg, url=None: (_mq.append(msg), 77)[1]
try:
    # 14 comparables serrés autour de 8 000 €, puis 30 annonces à 4 000 €
    _sq = _FauxSite([_annonce(prix=8000 + i * 20, km=140000 + i * 200)
                     for i in range(14)])
    runmod._source = lambda: _sq
    runmod.cmd_fast(once=True)            # amorçage silencieux
    _mq.clear()
    for i in range(30):
        _sq.publier(_annonce(prix=4000 + i, km=140100 + i * 5))
    runmod.cmd_fast(once=True)
    check(f"30 annonces méritantes → 30 notifications (reçu : {len(_mq)})",
          len(_mq) == 30)
finally:
    runmod.db.init, runmod.notify.envoyer_strict, runmod._source = _vi3, _vs3, _vsrc3
    _cq.close()


print("\n[35] DEAL SCORE — l'écart de prix DOMINE, la fiabilité ne fait que pondérer")

# Contrainte métier explicite : à +15 % du plancher, score < 50.
_PLANCHER = 6490
check(f"plancher {_PLANCHER} € × 1,15 → score < 50 "
      f"({score_prix(round(_PLANCHER * 1.15), _PLANCHER):.1f})",
      score_prix(round(_PLANCHER * 1.15), _PLANCHER) < 50)

# La même contrainte sur une dizaine de planchers différents : la règle
# porte sur l'ÉCART RELATIF, elle ne peut pas dépendre du niveau de prix.
for _p in (1500, 2450, 3500, 6490, 9990, 12750, 18000, 24500, 47000):
    check(f"plancher {_p} € × 1,15 → score < 50",
          score_prix(round(_p * 1.15), _p) < 50)

# Toute la courbe, pour qu'aucune formule bricolée sur un seul point ne
# puisse passer : monotone, bornée, et cohérente de bout en bout.
_courbe = [(0, 100.0), (5, 94.3), (10, 77.0), (15, 48.3), (20, 8.0), (25, 0.0)]
for _pct, _attendu in _courbe:
    _obtenu = score_prix(round(_PLANCHER * (1 + _pct / 100)), _PLANCHER)
    check(f"écart +{_pct:>2} % → {_attendu:.1f} (obtenu {_obtenu:.1f})",
          abs(_obtenu - _attendu) < 1.0)

_precedent = 101.0
for _pct in range(0, 40):
    _s = score_prix(round(_PLANCHER * (1 + _pct / 100)), _PLANCHER)
    check(f"la courbe ne remonte jamais (+{_pct} %)", _s <= _precedent + 1e-9)
    _precedent = _s

check("au prix du plancher → 100", score_prix(_PLANCHER, _PLANCHER) == 100.0)
check("sous le plancher → 100", score_prix(_PLANCHER - 1, _PLANCHER) == 100.0)

# ── LA FIABILITÉ NE PEUT JAMAIS AMÉLIORER UNE OPPORTUNITÉ ──
# C'est un invariant, pas un exemple : score = score_prix × fiabilité,
# avec fiabilité ∈ [0,45 ; 1,00]. On le vérifie exhaustivement.
_viol = []
_franchi = []
_SEUIL = 70.0
for _pct in range(-20, 60):
    _sp = score_prix(round(_PLANCHER * (1 + _pct / 100)), _PLANCHER)
    for _f in (0.45, 0.55, 0.70, 0.85, 0.93, 1.00):
        # invariant 1 : le produit ne dépasse jamais le score de prix
        if _sp * _f > _sp + 1e-9:
            _viol.append((_pct, _f))
        # invariant 2 — le vrai enjeu métier : une opportunité qui ne mérite
        # PAS d'alerte ne peut pas en mériter une grâce à la fiabilité.
        _final = round(max(0.0, min(100.0, _sp * _f)), 1)
        if _sp < _SEUIL <= _final:
            _franchi.append((_pct, _f))
check(f"la fiabilité ne peut JAMAIS augmenter le score de prix "
      f"({len(_viol)} violation(s) sur 480 combinaisons)", not _viol)
check(f"aucune mauvaise opportunité ne franchit 70 grâce à la fiabilité "
      f"({len(_franchi)} cas sur 480)", not _franchi)

# Et concrètement : une mauvaise opportunité reste mauvaise, quelle que
# soit la qualité de la comparaison.
for _pct in (15, 20, 25, 30):
    _sp = score_prix(round(_PLANCHER * (1 + _pct / 100)), _PLANCHER)
    check(f"+{_pct} % : même à fiabilité parfaite, jamais notifiable "
          f"({_sp * 1.0:.1f} < 70)", _sp * 1.00 < 70)

# Bornes et valeurs hostiles : aucun chemin ne sort de [0, 100].
_hostiles = [(None, 100), (100, None), ("x", 100), ([], 100), (0, 100),
             (100, 0), (-5, 100), (100, -5), (float("nan"), 100),
             (float("inf"), 100), (100, float("nan")), (100, float("inf")),
             (10**18, 1), (1, 10**18)]
_hs = [score_prix(a, b) for a, b in _hostiles]
check("aucune entrée hostile ne lève d'exception", len(_hs) == len(_hostiles))
check("aucune entrée hostile ne sort de [0,100]",
      all(0.0 <= v <= 100.0 for v in _hs))
check("aucun NaN ni inf en sortie",
      all(v == v and v not in (float("inf"), float("-inf")) for v in _hs))


print("\n[36] DÉFAILLANCES — crash, reprise, concurrence, Telegram")

import sqlite3 as _sq
import subprocess as _sp
import os as _os3
from datetime import datetime as _dt, timedelta as _td, timezone as _tz


class _SiteTest(_TS):
    """Site pilotable : stock, tri, panne, structure modifiée."""

    def __init__(self, stock=None, trie=True):
        super().__init__(delay=0)
        self.stock = list(stock or [])
        self.trie = trie
        self.panne = None
        self.pages_lues = 0

    def publier(self, *a):
        self.stock.extend(a)

    def _get(self, params, retries=2):
        self.pages_lues += 1
        if self.panne:
            self.derniere_erreur = self.panne
            return {}
        self.derniere_erreur = None
        lot = (sorted(self.stock, key=lambda r: int(r["itemId"][1:]), reverse=True)
               if self.trie else list(self.stock))
        off, lim = int(params.get("offset", 0)), int(params.get("limit", 100))
        return {"listings": lot[off:off + lim], "totalResultCount": len(lot)}


# `runmod.db` EST le module storage.db : le patcher patche le module.
# On garde donc une reference au VRAI `init` avant toute substitution.
_VRAI_INIT = _dbm.init


def _banc(nom):
    """Un banc d'essai isolé : base neuve, site simulé, Telegram capturé."""
    _dbm.init = _VRAI_INIT
    c = _base_neuve(_tmp(nom))
    envois = []
    etat = {"ko": False, "code": None}

    def faux_envoi(msg, url=None):
        if etat["ko"]:
            raise notify_mod.EchecTelegram(
                f"panne simulee {etat['code'] or ''}", code=etat["code"],
                retry_after=etat.get("retry_after", 0),
                definitif=etat["code"] in notify_mod.CODES_DEFINITIFS
                if etat["code"] else False)
        envois.append(msg)
        return 1000 + len(envois)

    runmod.db.init = lambda *a, **k: c
    runmod.notify.envoyer_strict = faux_envoi
    return c, envois, etat


def _marche(n=14, base=8000):
    return [_annonce(prix=base + i * 40, km=140000 + i * 300) for i in range(n)]


_sauve = (_VRAI_INIT, runmod.notify.envoyer_strict, runmod._source)
try:
    # ── a) crash APRÈS envoi Telegram, AVANT commit : aucune double alerte
    _c, _env, _et = _banc("f_crash_commit.db")
    _site = _SiteTest(_marche() + [_annonce(prix=5200, km=141000)])
    runmod._source = lambda: _site

    class _ConCrash:
        def __init__(self, c): object.__setattr__(self, "_c", c); object.__setattr__(self, "boum", False)
        def __getattr__(self, n):
            if n == "commit" and object.__getattribute__(self, "boum"):
                def _b(): raise _sq.OperationalError("disk I/O error simule")
                return _b
            return getattr(object.__getattribute__(self, "_c"), n)
        def __setattr__(self, n, v): object.__setattr__(self, n, v)

    _wrap = _ConCrash(_c)
    runmod.db.init = lambda *a, **k: _wrap

    # Le crash survient APRÈS le 3e envoi réel : le message est parti,
    # la ligne `alerts` n'a pas pu être écrite. C'est la fenêtre exacte
    # qui produisait une double alerte.
    _vrai_env = runmod.notify.envoyer_strict

    def _envoi_puis_crash(msg, url=None):
        r = _vrai_env(msg, url)
        if len(_env) >= 3:
            _wrap.boum = True
        return r

    runmod.notify.envoyer_strict = _envoi_puis_crash
    try:
        runmod.cmd_fast(once=True, amorcage_alerte=True)
    except Exception:
        pass
    runmod.notify.envoyer_strict = _vrai_env
    _wrap.boum = False
    _c.rollback()
    _avant_crash = list(_env)
    check(f"des messages sont bien partis avant le crash ({len(_avant_crash)})",
          len(_avant_crash) >= 3)
    _env.clear()
    runmod.cmd_fast(once=True, amorcage_alerte=True)
    # Ce qui compte n'est pas le NOMBRE de messages du cycle suivant — il
    # peut légitimement en partir pour d'autres annonces — mais le fait
    # qu'aucun message DÉJÀ PARTI ne reparte.
    _renvoyes = [m for m in _env if m in _avant_crash]
    check(f"après un crash post-envoi, aucun message déjà parti n'est "
          f"renvoyé (renvois : {len(_renvoyes)})", not _renvoyes)
    _dbm.init = _VRAI_INIT
    _c.close()

    # ── b) Telegram KO puis OK : rien de perdu, rien de dupliqué ──
    _c, _env, _et = _banc("f_tg_ko.db")
    runmod.db.init = lambda *a, **k: _c
    _site = _SiteTest(_marche() + [_annonce(prix=5100, km=141000)])
    runmod._source = lambda: _site
    _et["ko"] = True
    runmod.cmd_fast(once=True, amorcage_alerte=True)
    check("Telegram KO : aucune alerte enregistrée",
          _c.execute("SELECT COUNT(*) FROM alerts").fetchone()[0] == 0)
    _attente = notify_mod.en_attente(_c)
    check(f"mais l'intention est conservée en file ({_attente})", _attente > 0)
    _et["ko"] = False
    _b = notify_mod.reprendre(_c)
    check(f"le rétablissement délivre tout ({_b['delivrees']}/{_attente})",
          _b["delivrees"] == _attente and notify_mod.en_attente(_c) == 0)
    _n_alertes = _c.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
    notify_mod.reprendre(_c)
    check("une seconde reprise ne redélivre rien",
          _c.execute("SELECT COUNT(*) FROM alerts").fetchone()[0] == _n_alertes)
    _c.close()

    # ── c) 429 : on respecte retry_after et on n'insiste pas ──
    _c, _env, _et = _banc("f_429.db")
    runmod.db.init = lambda *a, **k: _c
    _site = _SiteTest(_marche() + [_annonce(prix=4900, km=141000)])
    runmod._source = lambda: _site
    _et.update(ko=True, code=429, retry_after=120)
    runmod.cmd_fast(once=True, amorcage_alerte=True)
    _lignes = _c.execute(
        "SELECT etat, prochain_essai, tentatives FROM outbox").fetchall()
    check("un 429 laisse la ligne à réessayer",
          all(l["etat"] == "a_envoyer" for l in _lignes) and len(_lignes) > 0)
    _futur = _c.execute(
        "SELECT COUNT(*) FROM outbox WHERE prochain_essai > datetime('now')"
    ).fetchone()[0]
    check(f"et repousse le prochain essai dans le futur ({_futur})", _futur > 0)
    _et.update(ko=False, code=None)
    _c.execute("UPDATE outbox SET prochain_essai=datetime('now','-1 hour')")
    _c.commit()
    _b = notify_mod.reprendre(_c)
    check(f"une fois l'attente écoulée, tout part ({_b['delivrees']})",
          _b["delivrees"] > 0 and notify_mod.en_attente(_c) == 0)
    _c.close()

    # ── d) 400 (message refusé) : erreur DÉFINITIVE, pas de boucle ──
    _c, _env, _et = _banc("f_400.db")
    runmod.db.init = lambda *a, **k: _c
    _site = _SiteTest(_marche() + [_annonce(prix=4800, km=141000)])
    runmod._source = lambda: _site
    _et.update(ko=True, code=400)
    runmod.cmd_fast(once=True, amorcage_alerte=True)
    check("un 400 marque la ligne en échec définitif",
          _c.execute("SELECT COUNT(*) FROM outbox WHERE etat='echec'"
                     ).fetchone()[0] > 0)
    check("et ne la rejoue pas indéfiniment",
          notify_mod.reprendre(_c)["reprises"] == 0)
    _c.close()

    # ── e) crash PENDANT l'envoi : sort inconnu, jamais renvoyé ──
    _c, _env, _et = _banc("f_interrompu.db")
    runmod.db.init = lambda *a, **k: _c
    _c.execute("INSERT INTO listings(source_id,external_id,title,price_eur,"
               "year,status,seller_type) VALUES(1,'z','Golf',5000,2015,"
               "'active','particulier')")
    _lz = _c.execute("SELECT id FROM listings").fetchone()["id"]
    _c.execute("INSERT INTO outbox(listing_id,cle_unique,etat,tier,deal_score,"
               "motif,message) VALUES(?,'k1','envoi_en_cours','great',88,"
               "'new','msg')", (_lz,))
    _c.commit()
    _b = notify_mod.reprendre(_c)
    check("un envoi interrompu est clos, pas renvoyé",
          _b["ambigues"] == 1 and len(_env) == 0)
    check("et il est tracé comme reçu pour ne pas ré-alerter",
          _c.execute("SELECT COUNT(*) FROM alerts WHERE listing_id=?",
                     (_lz,)).fetchone()[0] == 1)
    _c.close()

    # ── f) structure de l'API modifiée : rien n'est perdu ──
    _c, _env, _et = _banc("f_api.db")
    runmod.db.init = lambda *a, **k: _c
    _site = _SiteTest(_marche(12))
    runmod._source = lambda: _site
    runmod.cmd_fast(once=True)
    _f0 = runmod._watermark(_c, "fast")
    _casses = [_annonce(prix=3000 + i, km=139000 + i) for i in range(8)]
    for _a in _casses:
        _a["attributes"] = {x["key"]: x["value"] for x in _a["attributes"]}
    _site.publier(*_casses)
    runmod.cmd_fast(once=True)
    _f1 = runmod._watermark(_c, "fast")
    _maxi = max(int(a["itemId"][1:]) for a in _casses)
    check(f"API cassée : le filigrane ne dépasse PAS les annonces perdues "
          f"({_f1} < {_maxi})", _f1 < _maxi)
    check("le filigrane n'a pas reculé non plus", _f1 >= _f0)
    _c.close()

    # ── g) limite de pages : reprise, aucune annonce hors d'atteinte ──
    _c, _env, _et = _banc("f_pages.db")
    runmod.db.init = lambda *a, **k: _c
    _vmax = runmod.COLL["fast_loop_max_pages"]
    runmod.COLL["fast_loop_max_pages"] = 2
    try:
        _site = _SiteTest([_annonce(prix=4000 + i, km=140000 + i)
                           for i in range(450)])
        runmod._source = lambda: _site
        for _ in range(5):
            runmod.cmd_fast(once=True)
        _lues = _c.execute("SELECT COUNT(*) FROM listings").fetchone()[0]
        check(f"limite de pages : les 450 annonces finissent par être lues "
              f"({_lues})", _lues == 450)
    finally:
        runmod.COLL["fast_loop_max_pages"] = _vmax
    _c.close()

    # ── h) filigrane MONOTONE ──
    _dbm.init = _VRAI_INIT
    _c = _base_neuve(_tmp("f_filigrane.db"))
    runmod._set_watermark(_c, 5000, "fast")
    runmod._set_watermark(_c, 3000, "fast")
    check("le filigrane ne peut pas reculer",
          runmod._watermark(_c, "fast") == 5000)
    runmod._set_watermark(_c, 7000, "fast")
    check("mais il avance normalement",
          runmod._watermark(_c, "fast") == 7000)
    _c.close()

    # ── i) verrou : deux instances ne travaillent jamais ensemble ──
    _dbm.init = _VRAI_INIT
    _lv = _tmp("f_verrou.db")
    for _sfx in ("", "-wal", "-shm"):
        if _os3.path.exists(_lv + _sfx):
            _os3.remove(_lv + _sfx)
    _cv = _dbm.init(_lv)
    _script = (
        "import sys; sys.path.insert(0, %r)\n"
        "from carsniper.storage import db\n"
        "c = db.init(%r)\n"
        "print('OUI' if db.prendre_verrou(c, 'fast') else 'NON')\n"
        % (str(Path(__file__).resolve().parents[1]), _lv))
    check("l'instance A prend le verrou", _dbm.prendre_verrou(_cv, "fast"))
    _r = _sp.run([sys.executable, "-c", _script], capture_output=True, text=True)
    check("l'instance B (autre processus) est refusée", "NON" in _r.stdout)
    _dbm.rendre_verrou(_cv)
    _r2 = _sp.run([sys.executable, "-c", _script], capture_output=True, text=True)
    check("après libération, B peut travailler", "OUI" in _r2.stdout)
    _cv.close()

    # ── j) verrou d'un processus mort : repris, pas de blocage ──
    _cv = _dbm.connect(_lv)
    _cv.execute("INSERT INTO verrou(id,pid,hote,tache,pris_le,battement) "
                "VALUES(1,999999,'machine-morte','fast',"
                "datetime('now','-2 hours'),?) "
                "ON CONFLICT(id) DO UPDATE SET pid=excluded.pid, "
                "hote=excluded.hote, battement=excluded.battement",
                ((_dt.now(_tz.utc) - _td(hours=2))
                 .isoformat(timespec="seconds"),))
    _cv.commit()
    check("un verrou périmé est repris, il ne bloque pas éternellement",
          _dbm.prendre_verrou(_cv, "fast"))
    _cv.close()

finally:
    _dbm.init, runmod.notify.envoyer_strict, runmod._source = _sauve


print("\n[37] DONNÉES ET INVARIANTS — ce que le bot ne doit jamais faire")

_sv2 = (_VRAI_INIT, runmod.notify.envoyer_strict, runmod._source)
try:
    # ── la distance calculée survit à une revue d'annonce ──
    _dbm.init = _VRAI_INIT
    _cd = _base_neuve(_tmp("i_distance.db"))
    runmod.db.init = lambda *a, **k: _cd
    runmod.notify.envoyer_strict = lambda m, u=None: 1
    _sd = _SiteTest([_annonce(prix=5000 + i, km=140000 + i * 200)
                     for i in range(12)])
    runmod._source = lambda: _sd
    runmod.cmd_fast(once=True)
    _d1 = _cd.execute("SELECT distance_km FROM listings LIMIT 1").fetchone()[0]
    runmod.cmd_fast(once=True)
    _d2 = _cd.execute("SELECT distance_km FROM listings LIMIT 1").fetchone()[0]
    check(f"la distance calculée survit à une revue ({_d1} → {_d2})",
          _d1 is not None and _d1 == _d2)

    # ── une réponse partielle ne détruit pas une donnée connue ──
    _cible = _sd.stock[0]
    _cible["attributes"] = [a for a in _cible["attributes"]
                            if a["key"] != "mileage"]
    runmod.cmd_fast(once=True)
    _km = _cd.execute("SELECT mileage_km FROM listings WHERE external_id=?",
                      (_cible["itemId"],)).fetchone()[0]
    check(f"un attribut absent n'efface pas le kilométrage connu ({_km})",
          _km is not None)

    # Mais un retraitement DÉLIBÉRÉ doit pouvoir nettoyer une valeur
    # devenue invalide (kilométrage sentinelle, prix aberrant). Sans cette
    # distinction, la protection ci-dessus rendait toute correction
    # impossible : 351 annonces gardaient un kilométrage de 999 999.
    _sid_r = _dbm.source_id(_cd, "2ememain")
    _dbm.upsert_listing(_cd, _sid_r, _cible["itemId"],
                        {"title": "Golf", "mileage_km": None,
                         "price_eur": 5000, "price_type": "FIXED"},
                        reconstruire=True)
    _cd.commit()
    _km2 = _cd.execute("SELECT mileage_km FROM listings WHERE external_id=?",
                       (_cible["itemId"],)).fetchone()[0]
    check("un retraitement délibéré, lui, peut nettoyer la valeur",
          _km2 is None)
    _cd.execute("UPDATE listings SET mileage_km=? WHERE external_id=?",
                (_km, _cible["itemId"]))
    _cd.commit()

    # ── une annonce ingérée mais non analysée est reprise ──
    _cd.execute("UPDATE listings SET enriched_at=NULL WHERE external_id=?",
                (_cible["itemId"],))
    _cd.execute("DELETE FROM scores WHERE listing_id=("
                "SELECT id FROM listings WHERE external_id=?)",
                (_cible["itemId"],))
    _cd.commit()
    runmod.cmd_fast(once=True)
    check("une annonce jamais analysée est reprise au cycle suivant",
          _cd.execute("SELECT enriched_at FROM listings WHERE external_id=?",
                      (_cible["itemId"],)).fetchone()[0] is not None)
    _cd.close()

    # ── digest : un récapitulatif n'est pas une alerte ──
    _dbm.init = _VRAI_INIT
    _cg = _base_neuve(_tmp("i_digest.db"))
    _cg.execute("INSERT INTO listings(source_id,external_id,title,price_eur,"
                "year,mileage_km,status,seller_type) VALUES(1,'d1','Golf 1.4',"
                "5000,2015,120000,'active','particulier')")
    _lg = _cg.execute("SELECT id FROM listings").fetchone()["id"]
    _cg.execute("INSERT INTO alerts(listing_id,tier,deal_score,trigger_reason,"
                "sent_at) VALUES(?,'below',45,'digest',datetime('now'))", (_lg,))
    _cg.commit()
    _go, _ = notify_mod.should_notify(_cg, _lg, 88, "great", 5000,
                                      profile["antispam"])
    check("une ligne de récap n'empêche pas une vraie alerte à 88/100", _go)
    _cg.execute("INSERT INTO alerts(listing_id,tier,deal_score,trigger_reason,"
                "sent_at) VALUES(?,'great',88,'new',datetime('now'))", (_lg,))
    _cg.commit()
    _go2, _ = notify_mod.should_notify(_cg, _lg, 88, "great", 5000,
                                       profile["antispam"])
    check("mais une VRAIE alerte, elle, bloque bien la suivante", not _go2)

    # ── anti-republication : le kilométrage compte ──
    _cg.execute("INSERT INTO listings(source_id,external_id,title,price_eur,"
                "year,mileage_km,vkey,status,seller_type) VALUES(1,'d2',"
                "'Toyota Aygo',5000,2015,120000,'toyota|aygo|essence|manuelle|"
                "1.0|?','active','particulier')")
    _cg.execute("INSERT INTO listings(source_id,external_id,title,price_eur,"
                "year,mileage_km,vkey,status,seller_type) VALUES(1,'d3',"
                "'Toyota Aygo',5000,2015,120000,'toyota|aygo|essence|manuelle|"
                "1.0|?','active','particulier')")
    _cg.execute("INSERT INTO listings(source_id,external_id,title,price_eur,"
                "year,mileage_km,vkey,status,seller_type) VALUES(1,'d4',"
                "'Toyota Aygo',5000,2015,180000,'toyota|aygo|essence|manuelle|"
                "1.0|?','active','particulier')")
    _cg.commit()
    _a, _b2, _c2 = [r["id"] for r in _cg.execute(
        "SELECT id FROM listings WHERE external_id IN ('d2','d3','d4') "
        "ORDER BY external_id")]
    _cg.execute("INSERT INTO alerts(listing_id,tier,deal_score,trigger_reason,"
                "sent_at) VALUES(?,'great',88,'new',datetime('now'))", (_a,))
    _cg.commit()
    _r1, _ = notify_mod.should_notify(_cg, _b2, 88, "great", 5000,
                                      profile["antispam"])
    _r2, _ = notify_mod.should_notify(_cg, _c2, 88, "great", 5000,
                                      profile["antispam"])
    check("republication exacte (même km) → supprimée", not _r1)
    check("même titre/prix/année mais AUTRE kilométrage → notifiée", _r2)
    _cg.close()

    # ── carrosserie inconnue : jamais transformée en « berline » ──
    _vi = normalize_vehicle("Volkswagen Golf 1.4 TSI", "", 2016, None, None)
    check("carrosserie inconnue → « ? » dans la clé, pas « berline »",
          _vi.key().split("|")[5] == "?")
    check("carrosserie inconnue vs berline déclarée → comparaison FLOUE",
          _compat_ok("volkswagen|golf|essence|manuelle|1.4|?",
                     "volkswagen|golf|essence|manuelle|1.4|berline"))
    check("carrosserie inconnue vs SUV déclaré → comparaison possible aussi",
          _compat_ok("volkswagen|golf|essence|manuelle|1.4|?",
                     "volkswagen|golf|essence|manuelle|1.4|suv"))
    check("mais berline déclarée ≠ SUV déclaré",
          not _compat_ok("volkswagen|golf|essence|manuelle|1.4|berline",
                         "volkswagen|golf|essence|manuelle|1.4|suv"))

    # ── modèle numérique du site : génération ≠ modèle ──
    check("« Renault Clio » avec un site_model « 4 » n'est pas `renault|4`",
          normalize_vehicle("Renault Clio 1.2", "", 2016, None, None,
                            site_model="4").key().split("|")[1] != "4")
    check("mais « Mazda 2 » reste bien `mazda|2`",
          normalize_vehicle("Mazda 2 1.5", "", 2016, None, None,
                            site_model="2").key().split("|")[1] == "2")
    check("et « Polestar 2 » aussi",
          normalize_vehicle("Polestar 2", "", 2022, None, None,
                            site_model="2").key().split("|")[1] == "2")

    # ── km = 0 est une valeur valide ──
    _p0 = [{"price_eur": 15000 + i * 100, "year": 2024, "mileage_km": i * 10,
            "vkey": "toyota|aygo|essence|manuelle|1.0|?",
            "vkey_loose": "toyota|aygo", "seller_type": "particulier",
            "has_defect": False, "defauts_analyses": True,
            "norm_confidence": 0.9, "title": f"Aygo {i}"} for i in range(12)]
    _v0 = value_market({"year": 2024, "mileage_km": 0, "price_eur": 14000,
                        "vkey": "toyota|aygo|essence|manuelle|1.0|?"}, _p0)
    check(f"une voiture à 0 km est évaluable ({_v0.n} comparables)", _v0.n >= 8)

    # ── valeurs aberrantes bornées à la source ──
    _src = _TS(delay=0)
    _ab = _src.parse({"itemId": "m1", "title": "X",
                      "priceInfo": {"priceCents": 10 ** 15},
                      "attributes": [{"key": "mileage", "value": "9999999"},
                                     {"key": "constructionYear",
                                      "value": "9999"}]})
    check("un prix absurde est écarté, pas enregistré",
          _ab["price_eur"] is None)
    check("un kilométrage absurde est écarté", _ab["mileage_km"] is None)
    check("une année absurde est écartée", _ab["year"] is None)
    _ok0 = _src.parse({"itemId": "m1", "title": "X",
                       "priceInfo": {"priceCents": 500000},
                       "attributes": [{"key": "mileage", "value": "0"}]})
    check("mais 0 km reste une valeur valide", _ok0["mileage_km"] == 0)

    # ── la cible n'est jamais son propre comparable ──
    _VKJ = "toyota|aygo|essence|manuelle|1.0|?"

    def _cmp(p, k=120000):
        return {"price_eur": p, "year": 2015, "mileage_km": k, "vkey": _VKJ,
                "vkey_loose": "toyota|aygo", "seller_type": "particulier",
                "has_defect": False, "defauts_analyses": True,
                "norm_confidence": 0.9, "title": "Aygo"}

    _cible_j = {"year": 2015, "mileage_km": 120000, "vkey": _VKJ,
                "price_eur": 9000}
    _vj = value_market(_cible_j,
                       [_cmp(9000)] + [_cmp(11000 + i * 50, 120000 + i * 300)
                                       for i in range(11)])
    check(f"un jumeau exact est écarté du pool ({_vj.jumeaux} écarté)",
          _vj.jumeaux == 1 and _vj.pmin != 9000)
    _vk = value_market(_cible_j,
                       [_cmp(9000, 125000)] + [_cmp(11000 + i * 50,
                                                    120000 + i * 300)
                                               for i in range(11)])
    check("mais un vrai comparable au même prix est conservé",
          _vk.jumeaux == 0)
finally:
    _dbm.init, runmod.notify.envoyer_strict, runmod._source = _sv2


print("\n[38] RAFALE ET REPRISE — la file ne perd rien, n'affame pas le radar")

_sv3 = (_VRAI_INIT, runmod.notify.envoyer_strict, runmod._source)
try:
    _dbm.init = _VRAI_INIT
    _cr2 = _base_neuve(_tmp("i_rafale.db"))
    _envr = []
    _etr = {"ko": False}

    def _env_rafale(msg, url=None):
        if _etr["ko"]:
            raise notify_mod.EchecTelegram("indisponible")
        _envr.append(msg)
        return 900 + len(_envr)

    runmod.db.init = lambda *a, **k: _cr2
    runmod.notify.envoyer_strict = _env_rafale

    # 200 intentions d'un coup, Telegram indisponible.
    _cr2.execute("INSERT INTO listings(source_id,external_id,title,price_eur,"
                 "year,status,seller_type) VALUES(1,'raf','Golf',5000,2015,"
                 "'active','particulier')")
    _lr = _cr2.execute("SELECT id FROM listings").fetchone()["id"]
    _cr2.commit()
    for _i in range(200):
        _cr2.execute("INSERT INTO outbox(listing_id,cle_unique,etat,tier,"
                     "deal_score,motif,message) VALUES(?,?,'a_envoyer',"
                     "'great',88,'new',?)", (_lr, f"raf{_i}", f"message {_i}"))
    _cr2.commit()
    check("200 alertes en attente", notify_mod.en_attente(_cr2) == 200)

    _etr["ko"] = True
    _b1 = notify_mod.reprendre(_cr2, budget_s=0)
    check("Telegram KO : rien n'est délivré, rien n'est perdu",
          _b1["delivrees"] == 0 and notify_mod.en_attente(_cr2) == 200)

    # Telegram revient : la file part, mais SANS dépasser son budget de temps.
    _etr["ko"] = False
    _t0 = _t2.time()
    _b2 = notify_mod.reprendre(_cr2, budget_s=0.05)
    _duree = _t2.time() - _t0
    check(f"la reprise respecte son budget de temps ({_duree:.2f}s)",
          _duree < 5.0)
    check(f"et le reste attend le cycle suivant "
          f"({notify_mod.en_attente(_cr2)} en attente)",
          notify_mod.en_attente(_cr2) > 0 or _b2["delivrees"] == 200)

    # Cycles suivants : tout finit par partir, exactement une fois.
    for _ in range(30):
        if notify_mod.en_attente(_cr2) == 0:
            break
        notify_mod.reprendre(_cr2, budget_s=0)
    check(f"toutes les alertes finissent par partir ({len(_envr)}/200)",
          len(_envr) == 200)
    check("aucune n'est partie deux fois", len(set(_envr)) == 200)
    check("la file est vide", notify_mod.en_attente(_cr2) == 0)
    _cr2.close()

    # ── déposer deux fois la même intention n'annule pas le lot en cours ──
    _dbm.init = _VRAI_INIT
    _cd2 = _base_neuve(_tmp("i_depot.db"))
    _cd2.execute("INSERT INTO listings(source_id,external_id,title,price_eur,"
                 "year,status,seller_type) VALUES(1,'dep','Golf',5000,2015,"
                 "'active','particulier')")
    _ld = _cd2.execute("SELECT id FROM listings").fetchone()["id"]
    _cd2.commit()
    _o1 = notify_mod.deposer(_cd2, _ld, "m", None, "great", 88, "new", 5000)
    # travail NON COMMITÉ en cours, comme pendant une ingestion
    _cd2.execute("INSERT INTO listings(source_id,external_id,title,price_eur,"
                 "year,status,seller_type) VALUES(1,'encours','Polo',6000,"
                 "2016,'active','particulier')")
    _o2 = notify_mod.deposer(_cd2, _ld, "m", None, "great", 88, "new", 5000)
    check("une intention en double est refusée sans exception", _o2 is None)
    check("et le travail en cours n'est PAS annulé",
          _cd2.execute("SELECT COUNT(*) FROM listings WHERE external_id="
                       "'encours'").fetchone()[0] == 1)
    _cd2.close()
finally:
    _dbm.init, runmod.notify.envoyer_strict, runmod._source = _sv3


print("\n[39] RÈGLES MÉTIER FIXÉES — fenêtre 90 j, défaut neutre, aberrants")

_VKD = "toyota|aygo|essence|manuelle|1.0|?"


def _comp(p, k=120000, a=2015):
    return {"price_eur": p, "year": a, "mileage_km": k, "vkey": _VKD,
            "vkey_loose": "toyota|aygo", "seller_type": "particulier",
            "has_defect": False, "defauts_analyses": True,
            "norm_confidence": 0.9, "title": "Aygo"}


# ── 1. FENÊTRE DE MARCHÉ : 90 jours ──────────────────────────────────
_dbm.init = _VRAI_INIT
_cf = _base_neuve(_tmp("m_fenetre.db"))
_sidf = _dbm.source_id(_cf, "2ememain")


def _poser_dans_le_passe(ext, prix, jours):
    _cf.execute(
        "INSERT INTO listings(source_id,external_id,title,price_eur,year,"
        "mileage_km,vkey,vkey_loose,status,seller_type,published_at,"
        "first_seen_at) VALUES(?,?,'Toyota Aygo',?,2015,120000,?, "
        "'toyota|aygo','active','particulier',date('now',?),datetime('now',?))",
        (_sidf, ext, prix, _VKD, f"-{jours} days", f"-{jours} days"))


# une cible, 11 comparables récents, et 3 vieilles annonces bon marché
_poser_dans_le_passe("cible", 9000, 0)
for _i in range(11):
    _poser_dans_le_passe(f"recent{_i}", 11000 + _i * 50, _i)
for _i in range(3):
    _poser_dans_le_passe(f"vieux{_i}", 6000 + _i * 10, 120 + _i)
_cf.commit()
_idc = _cf.execute("SELECT id FROM listings WHERE external_id='cible'").fetchone()["id"]
_pf = runmod._pool(_cf, "toyota|aygo", _idc)
_prix_pool = sorted(c["price_eur"] for c in _pf)
check(f"la fenêtre de 90 j écarte les annonces trop vieilles "
      f"({len(_pf)} comparables retenus sur 14)", len(_pf) == 11)
check("aucune annonce de plus de 90 jours dans le pool",
      min(_prix_pool) >= 11000)

# et la fenêtre est bien celle de la configuration
check("la fenêtre vient de la configuration",
      int(profile["profile"].get("market_window_days", 0)) == 90)

# une annonce de 89 jours reste, une de 91 jours part
_poser_dans_le_passe("limite89", 7000, 89)
_poser_dans_le_passe("limite91", 7001, 91)
_cf.commit()
_pf2 = runmod._pool(_cf, "toyota|aygo", _idc)
_prix2 = {c["price_eur"] for c in _pf2}
check("une annonce de 89 jours est encore un comparable", 7000 in _prix2)
check("une annonce de 91 jours ne l'est plus", 7001 not in _prix2)
_cf.close()

# ── 2. UN DÉFAUT NE PEUT JAMAIS AMÉLIORER LE SCORE ───────────────────
_vd = Valuation(pmin=10000, p25=10500, p50=12000, p75=13000, n=14,
                confidence=0.9)
_vd.niveau = "strict"; _vd.iqr_ratio = 0.2
_vd.ancre_complete = True; _vd.flou_moyen = 0
_vehd = normalize_vehicle("Volkswagen Golf 1.4 TSI", "", 2015,
                          "Essence", "Manuelle")
_def1 = DefectHit(code="turbo", category="mechanical", severity=3,
                  matched="turbo", context="turbo casse", negated=False,
                  confidence=0.8, market_discount=(0, 0), pro_cost=(0, 0))
_def2 = DefectHit(code="accident", category="major", severity=4,
                  matched="schade", context="carrosserieschade", negated=False,
                  confidence=0.85, market_discount=(0, 0), pro_cost=(0, 0))

_pires = []
for _prix in range(2000, 14000, 250):
    _l = {"price_eur": _prix, "description": "x" * 300, "photo_count": 8,
          "year": 2015, "mileage_km": 120000}
    _sans = compute_deal(_l, _vehd, [], _vd, 14, 1, 0, None, profile)
    for _ds in ([_def1], [_def2], [_def1, _def2]):
        _avec = compute_deal(_l, _vehd, _ds, _vd, 14, 1, 0, None, profile)
        if _avec["deal_score"] > _sans["deal_score"] + 1e-9:
            _pires.append((_prix, [d.code for d in _ds],
                           _sans["deal_score"], _avec["deal_score"]))
check(f"sur 144 combinaisons prix × défauts, aucun défaut n'AMÉLIORE le "
      f"score ({len(_pires)} violation(s))", not _pires)

_franchit = []
for _prix in range(2000, 14000, 100):
    _l = {"price_eur": _prix, "description": "x" * 300, "photo_count": 8,
          "year": 2015, "mileage_km": 120000}
    _sans = compute_deal(_l, _vehd, [], _vd, 14, 1, 0, None, profile)
    _avec = compute_deal(_l, _vehd, [_def1], _vd, 14, 1, 0, None, profile)
    if _sans["tier"] == "below" and _avec["tier"] != "below":
        _franchit.append(_prix)
check(f"aucun défaut ne fait franchir le seuil à une annonce qui était "
      f"dessous ({len(_franchit)} cas)", not _franchit)

# le défaut reste DÉTECTÉ et AFFICHÉ, il n'est simplement plus pesé
_ld = {"price_eur": 8000, "description": "x" * 300, "photo_count": 8,
       "year": 2015, "mileage_km": 120000}
_rd = compute_deal(_ld, _vehd, [_def1], _vd, 14, 1, 0, None, profile)
check("le défaut reste présent dans le résultat",
      any(d["code"] == "turbo" for d in _rd["defauts_detail"]))
check("et le score de prix est strictement identique avec ou sans lui",
      _rd["score_prix"] == compute_deal(_ld, _vehd, [], _vd, 14, 1, 0,
                                        None, profile)["score_prix"])

# ── 3. ABERRANTS BAS : calibration FIGÉE pour cette version ──────────
# Ces valeurs verrouillent le comportement actuel. Toute recalibration
# fera échouer ces tests — c'est voulu.
_cible_ab = {"year": 2015, "mileage_km": 120000, "vkey": _VKD,
             "price_eur": 3000}
_marche_serre = [_comp(2900 + _i * 30, 120000 + _i * 200) for _i in range(11)]
_vab = value_market(_cible_ab, [_comp(1000)] + _marche_serre)
check(f"un prix très bas est écarté de l'ancre (exclus : {_vab.exclus})",
      1000 in _vab.exclus and _vab.pmin > 1000)
check("et il est SIGNALÉ, jamais masqué", len(_vab.exclus) > 0)
_vab2 = value_market(_cible_ab, [_comp(2500)] + _marche_serre)
check(f"sur un marché resserré, un comparable 15 % sous la médiane est "
      f"lui aussi écarté (ancre {_vab2.pmin}) — comportement figé, documenté",
      _vab2.pmin >= 2500)
_large = [_comp(2000 + _i * 400, 120000 + _i * 200) for _i in range(12)]
_vab3 = value_market(_cible_ab, _large)
check(f"sur un marché dispersé, rien n'est écarté à tort "
      f"(exclus : {_vab3.exclus})", not _vab3.exclus)
check("l'ancre est alors bien le prix le plus bas", _vab3.pmin == 2000)

# ── 4. ANCRE COMPLÈTE : règle conservée ──────────────────────────────
# Prix volontairement PROCHE du marché : on isole la règle de l'ancre
# complète, sans la mêler au filtre d'aberrants bas testé juste avant.
_incomplet = {**_comp(2860), "vkey": "toyota|aygo|?|?|?|?"}
_vac = value_market(_cible_ab, [_incomplet] + _marche_serre)
check(f"une moins chère à configuration trop incomplète n'est pas l'ancre "
      f"(ancre {_vac.pmin}, brute {_vac.moins_chere_brute})",
      _vac.pmin != 2860)
check("mais elle est rapportée comme moins chère brute",
      _vac.moins_chere_brute == 2860 and not _vac.ancre_complete)
_complet = _comp(2800)
_vad = value_market(_cible_ab, [_complet] + _marche_serre)
check("une moins chère bien identifiée reste l'ancre",
      _vad.pmin == 2800 and _vad.ancre_complete)

# ── 5. ABERRANTS HAUTS : hors statistiques, mais toujours comparables ─
_homogene = [_comp(3000 + _i * 25, 120000 + _i * 150) for _i in range(12)]
_vh1 = value_market(_cible_ab, _homogene)
_vh2 = value_market(_cible_ab, _homogene + [_comp(99000, 120500)])
check(f"un prix aberrant haut n'entre pas dans la médiane "
      f"({_vh1.p50} → {_vh2.p50})", abs(_vh2.p50 - _vh1.p50) <= 60)
check(f"ni dans la dispersion, donc ni dans la fiabilité "
      f"({_vh1.iqr_ratio:.2f} → {_vh2.iqr_ratio:.2f})",
      abs(_vh2.iqr_ratio - _vh1.iqr_ratio) < 0.05)
check(f"il est signalé comme écarté ({_vh2.exclus_hauts})",
      99000 in _vh2.exclus_hauts)
check("mais il reste COMPTÉ parmi les comparables (on ne retire pas une "
      "voiture du marché)", _vh2.n == _vh1.n + 1)
check("et il ne touche pas l'ancre, qui reste le prix le plus bas",
      _vh2.pmin == _vh1.pmin)
_vh3 = value_market(_cible_ab, _homogene)
check("sans aberrant haut, rien n'est écarté", not _vh3.exclus_hauts)


print("\n[40] DÉPLOIEMENT — sauvegarde avant retraitement")

# `reprocess.py` réécrit la base EN PLACE. Sans copie préalable, une
# interruption ou une régression du parser laissait l'utilisateur sans
# retour arrière possible.
import shutil as _sh
import importlib.util as _ilu

_spec = _ilu.spec_from_file_location(
    "_reproc_mod", Path(__file__).resolve().parent.parent / "reprocess.py")
_srcrp = (Path(__file__).resolve().parent.parent / "reprocess.py").read_text(
    encoding="utf-8")
check("reprocess.py sauvegarde avant d'écrire",
      "_sauvegarder(BASE)" in _srcrp and "shutil.copy2" in _srcrp)
check("et affiche la commande de retour arrière",
      "retour arriere" in _srcrp)

# Comportement réel de la fonction de sauvegarde, sans lancer tout le
# retraitement : une base existante est copiée, une base absente non.
_ns = {}
exec(_srcrp[_srcrp.index("def _sauvegarder"):
            _srcrp.index("_sauve = _sauvegarder(BASE)")],
     {"Path": Path, "datetime": _dt, "shutil": _sh}, _ns)
_sauvegarder = _ns["_sauvegarder"]

_bsrc = _tmp("depl_source.db")
_dbm.init(_bsrc).close()
_copie = _sauvegarder(_bsrc)
check(f"une base existante est copiée avant retraitement",
      _copie is not None and _os3.path.exists(_copie))
check("la copie est bien horodatée et distincte de l'original",
      _copie != _bsrc and "AVANT-REPROCESS-" in _copie)
check("la copie a le même contenu que l'original",
      _os3.path.getsize(_copie) == _os3.path.getsize(_bsrc))
_os3.remove(_copie)
_os3.remove(_bsrc)

_absente = _tmp("depl_inexistante.db")
if _os3.path.exists(_absente):
    _os3.remove(_absente)
check("une base inexistante ne déclenche pas de copie inutile",
      _sauvegarder(_absente) is None)

# Une base VIDE traversait les quatre passes en affichant « 0 » partout,
# sans jamais dire que rien n'avait été fait — le cas exact d'un chemin
# erroné. Le retraitement doit REFUSER, pas faire semblant.
_bvide = _tmp("depl_vide.db")
for _sfx in ("", "-wal", "-shm"):
    if _os3.path.exists(_bvide + _sfx):
        _os3.remove(_bvide + _sfx)
_dbm.init(_bvide).close()
_rv = _sp.run([sys.executable,
               str(Path(__file__).resolve().parent.parent / "reprocess.py"),
               _bvide], capture_output=True, text=True)
check("une base vide fait ÉCHOUER le retraitement au lieu d'afficher des zéros",
      _rv.returncode != 0)
check("et le message dit explicitement qu'il n'y a rien à retraiter",
      "AUCUNE annonce" in _rv.stdout)
for _f in _os3.listdir(_os3.path.dirname(_bvide)):
    if _f.startswith("depl_vide.AVANT-REPROCESS-"):
        _os3.remove(_os3.path.join(_os3.path.dirname(_bvide), _f))
_os3.remove(_bvide)


# ═══════════════════════════════════════════════════════════
#  ÉTAPE 41 — CLÉS D'ATTRIBUTS DU SITE ET REJEU DES PAYLOADS
# ═══════════════════════════════════════════════════════════
print("\n[41] EXTRACTION — les clés réellement publiées par 2ememain")

from carsniper.sources.twoememain import TweedehandsSource as _TS  # noqa: E402

_srcx = _TS()


def _brut(**attrs):
    """Payload minimal pour tester l'extraction des attributs. Nommé
    autrement que `_annonce` : une redéfinition masquait la fabrique du
    haut du fichier pour toutes les sections suivantes."""
    return {"itemId": "m1", "title": "test",
            "priceInfo": {"priceCents": 500000, "priceType": "FIXED"},
            "attributes": [{"key": k, "value": v} for k, v in attrs.items()]}


# Les clés du site sont `mileage` et `constructionYear` — mesurées sur
# 20 000 réponses brutes réelles : aucune autre variante n'existe.
_d = _srcx.parse(_brut(mileage="149000", constructionYear="2017"))
check("le kilométrage est lu sous la clé `mileage`", _d["mileage_km"] == 149000)
check("l'année est lue sous la clé `constructionYear`", _d["year"] == 2017)

# 999 999 est la valeur SENTINELLE « kilométrage non communiqué ».
check("le kilométrage sentinelle 999 999 est refusé, pas stocké",
      _srcx.parse(_brut(mileage="999999"))["mileage_km"] is None)

# La puissance : les clés lues jusqu'ici (`power`, `vermogen`) n'existent
# dans AUCUN payload réel. La colonne `power_kw` était vide pour les
# 53 599 annonces de la base — une donnée publiée, stockée nulle part.
check("la puissance est lue sous `enginePowerKW`, unité collée comprise",
      _srcx.parse(_brut(enginePowerKW="135 kW"))["power_kw"] == 135)
check("à défaut, les chevaux `engineHorsepowerBE` sont convertis en kW",
      _srcx.parse(_brut(engineHorsepowerBE="116 pk"))["power_kw"] == 85)
check("l'ancienne clé inventée `power` ne renvoie plus une valeur fantôme",
      _srcx.parse(_brut(power="150"))["power_kw"] is None)
check("sans attribut de puissance, la colonne reste vide",
      _srcx.parse(_brut(mileage="10000"))["power_kw"] is None)

print("\n[42] REJEU — une annonce a plusieurs réponses brutes")

# Le site renvoie l'annonce à chaque passage du radar et son contenu
# évolue : le vendeur complète le kilométrage, baisse le prix. Le
# retraitement doit repartir de l'état LE PLUS RÉCENT, sans perdre ce que
# le site avait donné plus tôt et qu'il ne renvoie plus.
_p1 = {"itemId": "m9", "title": "Opel Astra 2017",
       "priceInfo": {"priceCents": 575000, "priceType": "FIXED"},
       "attributes": [{"key": "constructionYear", "value": "2017"}]}
_p2 = {"itemId": "m9", "title": "Opel Astra 2017",
       "priceInfo": {"priceCents": 475000, "priceType": "FIXED"},
       "attributes": [{"key": "constructionYear", "value": "2017"},
                      {"key": "mileage", "value": "149000"}]}
_p3 = {"itemId": "m9", "title": "Opel Astra 2017",
       "priceInfo": {"priceCents": 475000, "priceType": "FIXED"},
       "attributes": [{"key": "constructionYear", "value": "2017"}]}


def _fusion(payloads):
    """Reproduit la fusion chronologique de `reprocess.py`."""
    cumul = {}
    for pl in payloads:
        for k, v in _srcx.parse(pl).items():
            if v is None and k in _dbm.JAMAIS_EFFACER and cumul.get(k) is not None:
                continue
            cumul[k] = v
    return cumul


_f = _fusion([_p1, _p2])
check("le rejeu retient le prix de la réponse LA PLUS RÉCENTE",
      _f["price_eur"] == 4750)
check("et le kilométrage apparu dans cette réponse",
      _f["mileage_km"] == 149000)

# Le cœur du bug corrigé : `GROUP BY external_id` avec deux agrégats
# contradictoires livrait la colonne nue `payload_text` de la PREMIÈRE
# réponse. Chaque retraitement ramenait donc l'annonce à sa version
# initiale : kilométrage effacé, prix remis à l'ancien.
check("le rejeu ne ramène PAS l'annonce à sa première version",
      _f["price_eur"] != 5750 and _f["mileage_km"] is not None)

# Et l'inverse : une réponse plus récente qui OMET un attribut ne doit
# pas effacer ce que le site avait déjà donné.
_f3 = _fusion([_p1, _p2, _p3])
check("un attribut absent d'une réponse récente n'efface pas la valeur connue",
      _f3["mileage_km"] == 149000)
check("mais le prix, lui, suit bien la dernière réponse", _f3["price_eur"] == 4750)

# Une valeur INVALIDE reste effacée : elle n'est retenue dans aucune
# réponse, donc la fusion ne peut pas la ressusciter.
_p4 = dict(_p2, attributes=[{"key": "constructionYear", "value": "2017"},
                            {"key": "mileage", "value": "999999"}])
check("une valeur invalide n'est ressuscitée par aucune réponse",
      _fusion([_p4])["mileage_km"] is None)

# La requête fautive elle-même, rejouée sur une vraie base : deux agrégats
# contradictoires dans un GROUP BY ne désignent aucune ligne.
_cx = _base_neuve(_tmp("carsniper_rejeu.db"))
_sidx = _dbm.source_id(_cx, "2ememain")
_dbm.store_raw(_cx, _sidx, "m9", None, _p1)
_dbm.store_raw(_cx, _sidx, "m9", None, _p2)
_cx.commit()
_rows = _cx.execute(
    "SELECT external_id, fetched_at, payload_text FROM raw_payloads "
    "WHERE source_id=? ORDER BY external_id, id", (_sidx,)).fetchall()
check("la lecture chronologique rend bien les DEUX réponses", len(_rows) == 2)
check("la fusion de ces deux lignes donne le prix courant",
      _fusion([_json.loads(r["payload_text"]) for r in _rows])["price_eur"] == 4750)

# `value_market` refuse d'évaluer sans année ni kilométrage : c'est ce
# refus qui met le score à 0 et la confiance à 0 %. Perdre le kilométrage
# au retraitement suffit donc à faire taire le radar.
check("sans kilométrage, aucune évaluation n'est possible",
      value_market({"year": 2017, "mileage_km": None, "vkey": "a|b|c|d|1.0|e"},
                   []).method == "insufficient_data")
check("sans année non plus",
      value_market({"year": None, "mileage_km": 149000, "vkey": "a|b|c|d|1.0|e"},
                   []).method == "insufficient_data")

# ═══════════════════════════════════════════════════════════
#  ÉTAPE 43 — DÉTECTION DU TRI ET ARRÊT AU FILIGRANE
# ═══════════════════════════════════════════════════════════
print("\n[43] TRI — reconnaître un flux chronologique réel")


def _lot(ids):
    return [{"itemId": f"m{i}"} for i in ids]


# Un flux parfait est évidemment reconnu.
check("un flux strictement décroissant est chronologique",
      runmod._ordre_par_date(_lot(range(2000, 1900, -1))))

# LE CAS QUI CASSAIT TOUT : le site place ses annonces mises en avant en
# tête de page, et les republications gardent leur ancien identifiant. Le
# flux reste chronologique, mais l'ancien critère — au plus 5 inversions
# entre voisins sur 100 — basculait à « pas trié » une page sur trois.
# Conséquence mesurée par l'utilisateur : 8 pages relues à chaque cycle,
# 43 s au lieu de 3 s.
_flux_reel = list(range(2000, 1900, -1))
for _pos, _vieux in ((0, 1500), (3, 1502), (17, 1509), (41, 1505),
                     (58, 1501), (73, 1507), (90, 1503)):
    _flux_reel[_pos] = _vieux
_anciennes_inversions = sum(1 for a, b in zip(_flux_reel, _flux_reel[1:]) if b > a)
check("un flux réel comporte plus d'inversions que l'ancien seuil n'en tolérait",
      _anciennes_inversions > 5)
check("et il est malgré tout reconnu comme chronologique",
      runmod._ordre_par_date(_lot(_flux_reel)))

# La contrepartie doit tenir : un tri par PERTINENCE ne doit jamais passer
# pour chronologique, sinon on s'arrête trop tôt et on rate des annonces.
_hasard = list(range(2000, 1900, -1))
_rnd.Random(7).shuffle(_hasard)
check("un flux mélangé n'est PAS pris pour un flux chronologique",
      not runmod._ordre_par_date(_lot(_hasard)))
_faux = sum(1 for _g in range(300)
            if (lambda v: (_rnd.Random(_g).shuffle(v), runmod._ordre_par_date(_lot(v)))[1])
            (list(range(2000, 1900, -1))))
check("sur 300 flux mélangés, aucun n'est pris pour un flux trié", _faux == 0)

check("un flux trié à l'envers est refusé",
      not runmod._ordre_par_date(_lot(range(1900, 2000))))
check("sous 20 annonces, on refuse de conclure plutôt que de deviner",
      not runmod._ordre_par_date(_lot(range(2000, 1985, -1))))

print("\n[44] RADAR — l'arrêt au filigrane évite la relecture du jour")

# Preuve par le comportement, pas par la lecture du code : avec un
# filigrane posé et un flux chronologique, le radar doit lire quelques
# pages, pas tout le jour.
_cs = _base_neuve(_tmp("carsniper_tri.db"))
_stock = [_annonce(prix=4000 + i) for i in range(500)]
_site_tri = _FauxSite(_stock)
_site_tri.limit = 100
_r0, _d0 = runmod._collecte_du_jour(_cs, _site_tri, verbose=False)
check("sans filigrane, le premier passage lit tout le flux", len(_r0) == 500)
runmod._set_watermark(_cs, _d0["filigrane_apres"], "fast")
_cs.commit()

# Trois nouveautés arrivent : elles sont en tête du flux trié.
_site_tri.publier(*[_annonce(prix=3000 + i) for i in range(3)])
_r1, _d1 = runmod._collecte_du_jour(_cs, _site_tri, verbose=False)
check("le flux est reconnu comme chronologique", _d1["tri_date"] is True)
check("le radar s'arrête au filigrane au lieu de relire le jour",
      _d1["arret"] == "filigrane atteint")
check("il ne lit que quelques pages, pas les six du flux", _d1["pages"] <= 3)
check("et les trois nouveautés sont bien dedans",
      len([r for r in _r1
           if runmod._numid(r["itemId"]) > _d0["filigrane_apres"]]) == 3)

# Le garde-fou reste actif : flux non trié -> relecture complète.
_cs2 = _base_neuve(_tmp("carsniper_tri2.db"))
_stock2 = [_annonce(prix=4000 + i) for i in range(300)]
_site_mel = _FauxSite(_stock2, trie_par_date=False)
_rnd.Random(3).shuffle(_site_mel.stock)
_site_mel.limit = 100
_r2, _d2 = runmod._collecte_du_jour(_cs2, _site_mel, verbose=False)
runmod._set_watermark(_cs2, _d2["filigrane_apres"], "fast")
_cs2.commit()
_r3, _d3 = runmod._collecte_du_jour(_cs2, _site_mel, verbose=False)
check("un flux non trié n'est jamais interrompu par le filigrane",
      _d3["arret"] != "filigrane atteint")
check("dans ce cas tout le flux est relu, rien n'est raté", len(_r3) == 300)

print(f"\n{'═'*54}\n  {ok} tests réussis, {fail} échecs\n{'═'*54}")
sys.exit(1 if fail else 0)
