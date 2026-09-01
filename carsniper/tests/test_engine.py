"""Test du moteur sur des cas réels reconstitués."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from carsniper.engine import (
    load_config, normalize_vehicle, detect_defects,
    value_market, compute_deal, Valuation,
    canon_fuel, vehicle_usable, score_confidence, estimate_repairs,
)

profile, lexicon = load_config()
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
check("et ne fait jamais baisser le score", res3["deal_score"] >= res["deal_score"])



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
check("run._pool filtre bien sur l.id <> ?", "l.id <> ?" in inspect.getsource(runmod._pool))

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
check("une annonce muette est moins fiable qu'une annonce qui s'explique",
      res_m["fiabilite"] < res_e["fiabilite"])

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
check("notification_threshold est lu depuis la config",
      "notification_threshold" in inspect.getsource(compute_deal))

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
    chemin = "/tmp/carsniper_test_feedback.db"
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

    ETAT["sendMessage_ok"] = True
    _parti2 = runmod._notifier(con, _lid2, _res_ko)
    check("et le tour suivant réussit bien à l'envoyer",
          _parti2 is True
          and con.execute("SELECT COUNT(*) FROM alerts").fetchone()[0] == _n_av + 1)
    con.close()
finally:
    _nf.urllib.request.urlopen = _vrai_urlopen
    _os.environ.pop("TELEGRAM_TOKEN", None)
    _os.environ.pop("TELEGRAM_CHAT_ID", None)


# ── 15. Traçabilité ────────────────────────────────────────
print("\n[15] TRAÇABILITÉ")
check("pmin est persisté dans valuations",
      "value_pmin" in inspect.getsource(runmod.analyse))
check("les comparables utilisés sont conservés",
      len(val_aygo.comparables) > 0)
check("une décision enregistre ce qui l'a limitée",
      "limites_json" in inspect.getsource(runmod._tracer_decision))
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


def _base_neuve(chemin="/tmp/carsniper_radar.db"):
    if _os2.path.exists(chemin):
        _os2.remove(chemin)
    for suf in ("-wal", "-shm"):
        if _os2.path.exists(chemin + suf):
            _os2.remove(chemin + suf)
    c = _db2.init(chemin)
    _db2.load_defects(c, lexicon)
    return c


# ── 16a. l'amorçage n'alerte pas, mais enregistre tout ─────
con = _base_neuve()
site = _FauxSite([_annonce(prix=4000 + i * 50) for i in range(12)])
envois = []
_vrai_send = runmod.notify.send
runmod.notify.send = lambda msg, url=None: (envois.append(msg), 1)[1]
try:
    raws, diag = runmod._collecte_du_jour(con, site, verbose=False)
    check("l'amorçage lit bien tout le flux du jour", len(raws) == 12)
    check("le tri par date est reconnu", diag["tri_date"] is True)
    seen, new = runmod._ingest(con, site, raws, "amorcage",
                               seller_known="particulier", alerter=False)
    check("les 12 annonces sont enregistrées", new == 12)
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
    runmod.notify.send = _vrai_send


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
    con = _base_neuve(f"/tmp/carsniper_remontee.db")
    runmod._set_watermark(con, _F, "fast")
    con.commit()
    raws, diag = runmod._collecte_du_jour(con, _SiteOrdonne(_ordre), verbose=False)
    neufs = len([r for r in raws if runmod._numid(r["itemId"]) > _F])
    check(f"{_nom} → aucune nouveauté ratée ({neufs}/{_attendu})", neufs == _attendu)

# la vraie frontière est bien détectée, elle
con = _base_neuve("/tmp/carsniper_frontiere.db")
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
con = _base_neuve("/tmp/carsniper_dates.db")
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
con = _base_neuve("/tmp/carsniper_ordre.db")
melange = [_annonce(prix=4000 + i * 50) for i in range(30)]
import random as _rnd
_rnd.Random(1).shuffle(melange)
site_melange = _FauxSite(melange, trie_par_date=False)
raws, diag = runmod._collecte_du_jour(con, site_melange, verbose=False)
check("un flux non trié par date est reconnu comme tel", diag["tri_date"] is False)
check("dans ce cas on lit tout le flux (rien n'est raté)", len(raws) == 30)

# le filigrane n'avance pas si l'ingestion échoue
con = _base_neuve("/tmp/carsniper_filigrane.db")
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
src_fast = _ins.getsource(runmod.cmd_fast)
check("cmd_fast attend entre deux cycles", "time.sleep" in src_fast)
check("la cadence vient de la configuration", "fast_loop_seconds" in src_fast)
check("cmd_loop ne relance pas une boucle infinie",
      "cmd_fast(once=True)" in _ins.getsource(runmod.cmd_loop))

# une passe unique se termine réellement
con = _base_neuve("/tmp/carsniper_once.db")
_vrai_init = runmod.db.init
runmod.db.init = lambda *a, **k: con
_vrai_source = runmod._source
runmod._source = lambda: _FauxSite([_annonce(prix=5000 + i * 40) for i in range(6)])
_vrai_send = runmod.notify.send
runmod.notify.send = lambda msg, url=None: 1
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
    runmod.notify.send = _vrai_send




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
check("aucun plafond de notifications ne subsiste dans le code",
      "night_max_alerts" not in _ins.getsource(runmod))
check("ni dans la configuration",
      "night_max_alerts" not in (Path(__file__).resolve().parent.parent / "config" / "profile.yaml").read_text())

_cn = _base_neuve("/tmp/carsniper_recalc.db")
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
_vrai_init2, _vrai_send2 = runmod.db.init, runmod.notify.send
runmod.db.init = lambda *a, **k: _cn
runmod.notify.send = lambda msg, url=None: (_envois.append(msg), 1)[1]
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
    runmod.db.init, runmod.notify.send = _vrai_init2, _vrai_send2
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


print(f"\n{'═'*54}\n  {ok} tests réussis, {fail} échecs\n{'═'*54}")
sys.exit(1 if fail else 0)
