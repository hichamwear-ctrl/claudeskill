#!/usr/bin/env python3
"""AUDIT DE RÉALISME DU RADAR COMMERCIAL.

Le moteur est éprouvé de l'intérieur. La question n'est plus « est-ce qu'il
tourne » mais « est-ce qu'il COMPREND ce qu'il va rencontrer ».

Cet audit ne rend pas un PASS/FAIL. Il rend une matrice de qualité, parce que
toutes les erreurs ne se valent pas :

    CORRECT        le moteur a conclu ce qu'un humain aurait conclu
    INCERTAIN      il a dit « je ne sais pas » là où on attendait une réponse —
                   coûteux, mais honnête : on perd du temps, pas une affaire
    INCORRECT      il a affirmé autre chose que la réalité — le seul cas grave :
                   annoncer POSTULABLE sur un marché fermé fait perdre une
                   journée de montage de dossier pour rien
    NON MESURABLE  l'épreuve elle-même ne permet pas de conclure

INCERTAIN est TOUJOURS meilleur qu'INCORRECT. L'audit les compte séparément et
ne les additionne jamais.

    python3 outils/audit_realisme.py
    python3 outils/audit_realisme.py --detail    # chaque écart, nommément
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

import yaml                                                     # noqa: E402

from radar.base import ouvrir                                   # noqa: E402
from radar.chaine import traiter                                # noqa: E402
from radar.mode import Mode                                     # noqa: E402
from radar.modele import Opportunite                            # noqa: E402
from radar.procedure import Vocabulaire, lire                   # noqa: E402
from radar import rapport as rapport_mod                        # noqa: E402
from outils.familles import moteur                              # noqa: E402

MAINTENANT = datetime(2026, 9, 3, tzinfo=timezone.utc)
CORRECT, INCERTAIN, INCORRECT, NON_MESURABLE = (
    "CORRECT", "INCERTAIN", "INCORRECT", "NON MESURABLE")


class Matrice:
    """Compte par dimension, sans jamais confondre incertain et incorrect."""

    def __init__(self):
        self.par_dimension: dict[str, Counter] = {}
        self.ecarts: list = []

    def noter(self, dimension, verdict, detail=""):
        self.par_dimension.setdefault(dimension, Counter())[verdict] += 1
        if verdict in (INCORRECT, INCERTAIN):
            self.ecarts.append((verdict, dimension, detail))

    def afficher(self):
        print(f"  {'DIMENSION':<22}{'CORRECT':>9}{'INCERTAIN':>11}"
              f"{'INCORRECT':>11}{'NON MES.':>10}   qualité")
        for dim, c in self.par_dimension.items():
            total = sum(c.values())
            mesurables = total - c[NON_MESURABLE]
            part = f"{c[CORRECT] / mesurables:.0%}" if mesurables else "n/d"
            alerte = "  ⚠" if c[INCORRECT] else ""
            print(f"  {dim:<22}{c[CORRECT]:>9}{c[INCERTAIN]:>11}"
                  f"{c[INCORRECT]:>11}{c[NON_MESURABLE]:>10}   {part}{alerte}")

    @property
    def incorrects(self):
        return sum(c[INCORRECT] for c in self.par_dimension.values())


def _etat_lu(lecture) -> str:
    if lecture.etat.value == "INCONNU" and not lecture.procedure_detectee:
        return "HORS_PROCEDURE"
    return {"POSTULABLE": "POSTULABLE", "ATTRIBUÉ": "ATTRIBUE", "FERMÉ": "FERME",
            "ANNULÉ": "ANNULE", "INFRUCTUEUX": "INFRUCTUEUX", "ANNONCÉ": "ANNONCE",
            "INFORMATIF": "INFORMATIF", "INCONNU": "INCONNU"}[lecture.etat.value]


# ═══════════════════════════════════════════════ 1. le corpus de formulations
def epreuve_corpus(m: Matrice, detail: bool):
    corpus = yaml.safe_load(
        (RACINE / "validation" / "corpus_formulations.yaml").read_text(encoding="utf-8"))
    print(f"\n1 · CORPUS DE FORMULATIONS — {len(corpus['formulations'])} phrases, "
          f"4 langues")
    print(f"    origine : {corpus['meta']['origine_par_defaut']} · "
          f"pages réelles observées : {corpus['meta']['pages_reelles_observees']}")

    incomprises, ambigues = [], []
    for f in corpus["formulations"]:
        # Une valeur de champ de statut n'est pas de la prose : le portail
        # affirme qu'il y a une procédure, même quand sa valeur est illisible.
        if f.get("champ") == "statut":
            lecture = lire(statut_source=f["texte"], source="portail-test")
        else:
            lecture = lire(texte=f["texte"])
        obtenu = _etat_lu(lecture)
        attendu = f["attendu"]
        dim = "état · " + f["langue"]

        if obtenu == attendu:
            verdict = CORRECT
        elif obtenu in ("INCONNU", "HORS_PROCEDURE") and attendu != "INCONNU":
            verdict = INCERTAIN
            incomprises.append((f["texte"], f["langue"], attendu, obtenu))
        else:
            verdict = INCORRECT
            ambigues.append((f["texte"], f["langue"], attendu, obtenu,
                             str(lecture.preuves[0]) if lecture.preuves else "—"))
        m.noter(dim, verdict, f"« {f['texte'][:52]} » attendu {attendu}, lu {obtenu}")

    if incomprises:
        print(f"\n    NON COMPRISES ({len(incomprises)}) — le moteur a dit « je ne "
              f"sais pas »")
        for t, lg, att, obt in incomprises[:20] if not detail else incomprises:
            print(f"      [{lg}] {t[:56]:<58} attendu {att}")
    if ambigues:
        print(f"\n    MAL COMPRISES ({len(ambigues)}) — le moteur a affirmé autre chose")
        for t, lg, att, obt, pr in ambigues:
            print(f"      [{lg}] {t[:52]:<54} attendu {att}, lu {obt}")
            print(f"            preuve : {pr[:74]}")
    return incomprises, ambigues


# ═══════════════════════════════════════════ 2. le portail et ses contradictions
VARIANTES_PORTAIL = [
    ("rubrique en cours + texte clôturé", "Marchés en cours",
     "La procédure est clôturée.", None, "FERME"),
    ("rubrique en cours + date dépassée", "Marchés en cours", "", -30, "FERME"),
    ("rubrique en cours + date future", "Marchés en cours", "", +60, "POSTULABLE"),
    ("rubrique attribué sans titulaire", "Résultats",
     "La fiche ne mentionne aucun titulaire.", None, "ATTRIBUE"),
    ("fiche : attribution prochaine", "Marchés en cours",
     "L'attribution sera prononcée prochainement.", None, "INCONNU"),
    ("fiche : procédure infructueuse", "Marchés en cours",
     "La procédure a été déclarée infructueuse.", None, "INFRUCTUEUX"),
    ("fiche : consultation en cours", "Marchés en cours",
     "La consultation est en cours, les offres sont recevables.", +60, "POSTULABLE"),
    ("ouverte le 1er juin, remise expirée le 30 juin", "Marchés en cours",
     "Consultation ouverte le 1er juin. Le délai de remise des offres a expiré "
     "le 30 juin.", None, "FERME"),
    ("avis initial visible mais marché attribué", "Marchés en cours",
     "Marché attribué à Transport National SA. L'avis initial reste visible.",
     None, "ATTRIBUE"),
    ("rubrique inconnue du portail", "Phase Gamma", "", None, "INCONNU"),
]


def epreuve_portail(m: Matrice, detail: bool):
    print("\n2 · PORTAIL — la rubrique contre le contenu de la fiche")
    voc = Vocabulaire(yaml.safe_load(
        (RACINE / "sources" / "portail.yaml").read_text(encoding="utf-8")))
    for nom, rubrique, texte, jours, attendu in VARIANTES_PORTAIL:
        echeance = MAINTENANT + timedelta(days=jours) if jours else None
        lecture = lire(type_information=rubrique, texte=texte, echeance=echeance,
                       maintenant=MAINTENANT, vocabulaire=voc, source="portail")
        obtenu = _etat_lu(lecture)
        if obtenu == attendu:
            verdict = CORRECT
        elif obtenu == "INCONNU":
            verdict = INCERTAIN
        else:
            verdict = INCORRECT
        m.noter("portail · contradictions", verdict,
                f"{nom} : attendu {attendu}, lu {obtenu}")
        marque = {CORRECT: "✔", INCERTAIN: "~", INCORRECT: "✗"}[verdict]
        print(f"    {marque} {nom:<44} {obtenu:<15} ({lecture.confiance.value})")
        if verdict is not CORRECT or detail:
            print(f"       attendu {attendu}"
                  + (f" · {lecture.contradictions[0][:62]}"
                     if lecture.contradictions else ""))


# ═══════════════════════════════════════════════════ 3. les lots indépendants
def epreuve_lots(m: Matrice, detail: bool):
    from radar.modele import LotBrut
    print("\n3 · LOTS — quatre états dans un même marché")
    voc = Vocabulaire(yaml.safe_load(
        (RACINE / "sources" / "bda.yaml").read_text(encoding="utf-8")))
    voc.statuts.update(Vocabulaire({"procedure": {"statuts": {
        "infructueux": {"interpretation": "infructueux", "confiance": "elevee"},
        "préinformation": {"interpretation": "annonce", "confiance": "elevee"}}}}).statuts)
    mot = moteur()
    mot.vocabulaires["bda"] = voc
    marche = Opportunite(
        source="bda", ref_source="AUDIT-LOTS", statut_source="attribué",
        intitule="Marché de services logistiques", texte="transport et distribution",
        acheteur="Province", pays_livraison=["BE"],
        echeance_brute="2099-06-01T12:00:00+02:00", cpv=["60000000"],
        lots=[LotBrut(numero="1", intitule="Transport de mobilier",
                      statut_source="attribué", montant=60000),
              LotBrut(numero="2", intitule="Distribution urbaine",
                      statut_source="en cours", montant=90000),
              LotBrut(numero="3", intitule="Manutention",
                      statut_source="annulé", montant=40000),
              LotBrut(numero="4", intitule="Transport futur",
                      statut_source="préinformation", montant=70000)])
    attendus = {"1": "ATTRIBUÉ", "2": "POSTULABLE", "3": "ANNULÉ", "4": "ANNONCÉ"}
    cx = ouvrir(":memory:")
    traiter(cx, mot, [marche], maintenant_dt=MAINTENANT)
    lignes = {l["lot_numero"]: l for l in cx.execute(
        "SELECT lot_numero, etat_procedure, action, score, montant, marche_ref"
        " FROM opportunites")}
    for numero, attendu in attendus.items():
        l = lignes.get(numero)
        if l is None:
            m.noter("lots · état propre", INCORRECT, f"lot {numero} absent")
            print(f"    ✗ lot {numero} : ABSENT")
            continue
        obtenu = l["etat_procedure"]
        verdict = (CORRECT if obtenu == attendu
                   else INCERTAIN if obtenu == "INCONNU" else INCORRECT)
        m.noter("lots · état propre", verdict,
                f"lot {numero} : attendu {attendu}, lu {obtenu}")
        marque = {CORRECT: "✔", INCERTAIN: "~", INCORRECT: "✗"}[verdict]
        print(f"    {marque} lot {numero} → {obtenu:<12} {(l['action'] or '')[:24]:<26}"
              f"score {l['score']:>3}  montant {l['montant']}  parent {l['marche_ref']}")
    distincts = len({l["etat_procedure"] for l in lignes.values()})
    m.noter("lots · état propre", CORRECT if distincts == 4 else INCORRECT,
            f"{distincts} états distincts sur 4 attendus")
    print(f"    → {distincts} états distincts (le parent n'écrase pas les lots)")


# ══════════════════════════════════════════ 4. cent opportunités mélangées
REPARTITION = [("public", 25), ("prive", 25), ("sous_traitance", 15),
               ("partenariat", 10), ("signal", 10), ("a_demarcher", 10),
               ("metier_nouveau", 5)]


def _cent_opportunites():
    """Cent besoins, sept catégories, mélangés. La catégorie n'est PAS donnée
    au moteur : il doit la retrouver depuis ce que l'opportunité EST."""
    import random
    lot = []
    for categorie, n in REPARTITION:
        for i in range(n):
            base = dict(pays_livraison=["BE"], montant=90000 + i * 1100,
                        duree_mois=24, cadence="quotidienne",
                        distance_depot_km=15 + i % 50,
                        echeance_brute="2099-05-15T12:00:00+02:00")
            if categorie == "public":
                o = Opportunite(source="bda", ref_source=f"PUB-{i}",
                                intitule=f"Transport et distribution — lot {i}",
                                texte="tournées quotidiennes de distribution",
                                acheteur=f"Commune {i}", secteur_acheteur="public",
                                cpv=["60000000"], type_avis="avis de marché",
                                statut_source="en cours", **base)
            elif categorie == "prive":
                o = Opportunite(source="entreprise", ref_source=f"PRV-{i}",
                                intitule=f"Nous recherchons un transporteur — site {i}",
                                texte="livraisons quotidiennes pour le compte de tiers",
                                acheteur=f"Société {i}", secteur_acheteur="privé", **base)
            elif categorie == "sous_traitance":
                o = Opportunite(source="entreprise", ref_source=f"SST-{i}",
                                intitule=f"Appel à sous-traitants transport — zone {i}",
                                texte="sous-traitance de tournées de distribution",
                                acheteur=f"Opérateur {i}", secteur_acheteur="privé", **base)
            elif categorie == "partenariat":
                o = Opportunite(source="entreprise", ref_source=f"PRT-{i}",
                                intitule=f"Devenir partenaire transporteur — réseau {i}",
                                texte="nous confions nos tournées à des partenaires",
                                acheteur=f"Réseau {i}", secteur_acheteur="privé", **base)
            elif categorie == "signal":
                o = Opportunite(source="signaux", ref_source=f"SIG-{i}",
                                intitule=f"Recrutement de chauffeurs — site {i}",
                                texte="distribution urbaine, tournées quotidiennes",
                                acheteur=f"Entreprise {i}", secteur_acheteur="privé",
                                est_signal=True, signal_code="recrutement_massif", **base)
            elif categorie == "a_demarcher":
                sans_date = dict(base); sans_date["echeance_brute"] = None
                o = Opportunite(source="brave", ref_source=f"DEM-{i}",
                                intitule=f"Distributeur régional {i}",
                                texte="livraisons quotidiennes, flotte interne saturée",
                                acheteur=f"Distributeur {i}", secteur_acheteur="privé",
                                **sans_date)
            else:
                # Dates COHÉRENTES : dépôt d'abord, démarrage ensuite. La
                # première version avait une échéance en 2099 et un démarrage
                # en 2029 — une contradiction, qui a d'ailleurs révélé un vrai
                # défaut du moteur (délai négatif traité comme insuffisant).
                coherent = dict(base)
                coherent["echeance_brute"] = "2028-03-01T12:00:00+01:00"
                o = Opportunite(source="entreprise", ref_source=f"MET-{i}",
                                intitule=f"Partenaires installation bornes — zone {i}",
                                texte="véhicules utilitaires et personnel de terrain, "
                                      "formation complète de trois semaines assurée "
                                      "au démarrage",
                                acheteur=f"Opérateur énergie {i}",
                                secteur_acheteur="privé", date_demarrage="2028-09-01",
                                **coherent)
            lot.append((categorie, o))
    random.Random(20260903).shuffle(lot)
    return lot


ATTENDU_FAMILLE = {
    "public": "MARCHÉS PUBLICS", "prive": "BESOINS PRIVÉS",
    "sous_traitance": "BESOINS PRIVÉS", "partenariat": "BESOINS PRIVÉS",
    "signal": "SIGNAUX ÉCONOMIQUES", "a_demarcher": "ENTREPRISES À DÉMARCHER",
    "metier_nouveau": "MÉTIERS À CONSTRUIRE",
}


def epreuve_cent(m: Matrice, detail: bool):
    print("\n4 · CENT OPPORTUNITÉS MÉLANGÉES — la catégorie n'est pas donnée")
    lot = _cent_opportunites()
    cx = ouvrir(":memory:")
    b = traiter(cx, moteur(), [o for _, o in lot], maintenant_dt=MAINTENANT)
    par_ref = {o.ref_source: c for c, o in lot}
    from radar.rapport import famille_de
    confusion: dict = {}
    for l in cx.execute(
            "SELECT a.ref_source, o.score, o.intitule, o.type, o.action, o.nature,"
            " o.etat_procedure, o.echeance, o.secteur FROM opportunites o"
            " JOIN avis a ON a.id = o.avis_id WHERE o.type <> 'REJET'"):
        categorie = par_ref.get(l["ref_source"])
        if categorie is None:
            continue
        attendu = ATTENDU_FAMILLE[categorie]
        obtenu = famille_de(l)
        confusion.setdefault(categorie, Counter())[obtenu] += 1
        m.noter("familles retrouvées", CORRECT if obtenu == attendu else INCORRECT,
                f"{categorie} → {obtenu} (attendu {attendu})")
    print(f"    {b.lus} lus · écart de réconciliation {b.livre.ecart()}")
    for categorie, n in REPARTITION:
        c = confusion.get(categorie, Counter())
        attendu = ATTENDU_FAMILLE[categorie]
        bon = c[attendu]
        autres = " · ".join(f"{k}×{v}" for k, v in c.items() if k != attendu)
        marque = "✔" if bon == n else "✗"
        print(f"    {marque} {categorie:<16} {bon:>3}/{n:<4} → {attendu:<26}"
              + (f"  confondu avec {autres}" if autres else ""))


# ═══════════════════════ 5. le même besoin sous six capteurs — score identique
def epreuve_six_capteurs(m: Matrice, detail: bool):
    print("\n5 · MÊME BESOIN, SIX CAPTEURS — le score doit être identique")
    commun = dict(intitule="Distribution urbaine de marchandises",
                  texte="tournées quotidiennes de distribution urbaine",
                  acheteur="Client", montant=180000, duree_mois=24,
                  cadence="quotidienne", pays_livraison=["BE"],
                  distance_depot_km=20, echeance_brute="2099-05-15T12:00:00+02:00",
                  exigences={"licence_transport": True})
    formes = {
        "ted": dict(source="ted", cpv=["60000000"], type_avis="contract-notice"),
        "bda": dict(source="bda", cpv=["60000000"], type_avis="avis de marché"),
        "recherche": dict(source="brave"),
        "entreprise": dict(source="entreprise"),
        "bourse_fret": dict(source="bourse_fret"),
        "signal": dict(source="signaux", est_signal=True),
    }
    mot = moteur()
    scores, capacites = {}, {}
    for nom, forme in formes.items():
        o = Opportunite(ref_source=f"SIX-{nom}", **{**commun, **forme})
        r = mot.analyser(o, MAINTENANT)
        scores[nom] = r.score.total
        capacites[nom] = tuple(r.bilan.bloquants) + tuple(r.bilan.mobilisations)
        print(f"    {nom:<14} score {r.score.total:>3}  "
              f"{r.classement.type.value:<13}{r.nature.value:<10}"
              f"{r.classement.action.value[:24]}")
    m.noter("neutralité du capteur", CORRECT if len(set(scores.values())) == 1
            else INCORRECT, f"scores : {scores}")
    m.noter("neutralité du capteur", CORRECT if len(set(capacites.values())) == 1
            else INCORRECT, "capacités")
    print(f"    → {len(set(scores.values()))} score distinct, "
          f"{len(set(capacites.values()))} capacité distincte")


def principal(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--detail", action="store_true")
    a = p.parse_args(argv)

    print("╔" + "═" * 70 + "╗")
    print("║  AUDIT DE RÉALISME — RADAR COMMERCIAL                                 ║")
    print("║                                                                      ║")
    print("║  MODE : TEST — toutes les formulations sont ÉCRITES, pas observées.  ║")
    print("║  DONNÉES RÉELLES OBSERVÉES : 0                                       ║")
    print("║  Aucune page réelle n'a été consultée. Cet audit mesure ce que le    ║")
    print("║  moteur comprend de phrases vraisemblables — pas du monde réel.      ║")
    print("╚" + "═" * 70 + "╝")

    m = Matrice()
    incomprises, ambigues = epreuve_corpus(m, a.detail)
    epreuve_portail(m, a.detail)
    epreuve_lots(m, a.detail)
    epreuve_cent(m, a.detail)
    epreuve_six_capteurs(m, a.detail)

    print("\n" + "═" * 72)
    print("MATRICE DE QUALITÉ")
    print("  INCERTAIN coûte du temps · INCORRECT coûte une affaire. "
          "Jamais additionnés.\n")
    m.afficher()
    print(f"\n  formulations non comprises : {len(incomprises)}")
    print(f"  formulations mal comprises : {len(ambigues)}"
          + ("   ⚠ chacune est une affaire potentiellement perdue" if ambigues else ""))
    print("  DONNÉES RÉELLES OBSERVÉES  : 0")

    print("\n" + "─" * 72)
    print("CE QUE CET AUDIT NE PROUVE PAS")
    print("""
  Ce corpus a été ÉCRIT PAR LA MACHINE QUI EST ÉVALUÉE, puis le moteur a été
  corrigé jusqu'à le passer. Un score de 100 % y mesure donc surtout la
  cohérence entre deux choses écrites par le même auteur.

  Ce qu'il prouve réellement :
    · les défauts qu'il a trouvés étaient RÉELS — « offres non recevables »
      ressortait POSTULABLE, une date dépassée perdait contre une rubrique ;
    · le moteur ne se contredit plus sur les cas qu'on a su imaginer ;
    · aucune régression ne passera plus sur ces 78 formulations.

  Ce qu'il ne prouve pas :
    · qu'un portail réel emploie ces tournures-là ;
    · qu'il n'en emploie pas d'autres, absentes d'ici ;
    · qu'une vraie page se lit comme une chaîne de caractères propre.

  La seule chose qui lèvera ce doute est une page réellement collectée. Tant
  que la ligne « DONNÉES RÉELLES OBSERVÉES » affiche 0, ce rapport décrit une
  cohérence interne, pas une compétence face au monde.""")
    return 1 if m.incorrects else 0


if __name__ == "__main__":
    sys.exit(principal())
