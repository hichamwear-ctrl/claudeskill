#!/usr/bin/env python3
"""Audit du cahier des charges — chaque règle est-elle tenue par du code ET des tests ?

Le radar ne doit jamais devenir une boîte noire, et cette exigence vaut aussi
pour le projet lui-même : une règle validée puis perdue lors d'une réécriture
est un risque réel — c'est arrivé une fois avec les seize questions.

    python3 outils/audit_cahier.py

Renvoie un code non nul si une règle n'est plus couverte.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent

# (règle, modules qui l'implémentent, fragments de noms de tests attendus)
REGLES = [
    ("1  aucune priorité fixe de source", ["registre"],
     ["priorites_initiales_sont_non_mesurees", "score_ne_depend_pas_de_la_source"]),
    ("2  appel d'offres traité comme les autres", ["classification"],
     ["score_ne_depend_pas_de_la_source", "petit_contrat_recurrent"]),
    ("3  Google = découverte, jamais un rejet par mot-clé", ["decouverte"],
     ["metier_inconnu_n_est_jamais_rejete", "requetes_sont_reellement_generees"]),
    ("4  CAPTER / DÉVELOPPER séparés", ["classification"],
     ["attribution_va_dans_developper", "attribution_ne_dit_jamais_postuler"]),
    ("5  ma taille n'est jamais un rejet", ["capacite"],
     ["trop_gros_pour_moi_seul_donne_prospect", "aucun_de_ces_cas_n_est_un_rejet"]),
    ("6  🟣 six conditions, formation ≠ obligation légale", ["construction"],
     ["metier_inconnu_avec_formation", "formation_n_efface_pas_une_obligation"]),
    ("7  l'économie prime sur le montant", ["score"],
     ["petit_contrat_recurrent_proche_bat", "marge_reste_non_mesuree"]),
    ("8  données manquantes jamais inventées", ["statut", "fiche"],
     ["aucune_date_n_est_jamais_inventee", "montant_absent_n_est_jamais_invente"]),
    ("9  lot par lot et prestation ≠ fourniture", ["lots", "role"],
     ["seul_le_lot_compatible_est_notifie", "fourniture_et_livraison_de_poissons"]),
    ("10 déduplication à trois niveaux", ["deduplication"],
     ["sans_date_commune_reste_un_doublon_possible",
      "avec_meme_echeance_est_un_doublon_probable"]),
    ("11 DEMO et RÉEL structurellement séparés", ["mode"],
     ["fixture_est_refusee_en_reel", "deux_modes_n_utilisent_jamais_la_meme_base"]),
    ("12 livre de comptes, arrêt sur perte", ["comptes"],
     ["disparition_sans_motif_fait_echouer", "brutes_non_ventilees_font_echouer"]),
    ("13 sources réellement consultées", ["registre"],
     ["source_est_jamais_consultee_par_defaut", "source_non_consultee_n_a_pas_de_priorite"]),
    ("14 rapport de mesure, sans TOP forcé", ["rapport"],
     ["rapport_porte_son_mode_en_tete", "sans_opportunite_le_rapport_le_dit"]),
    ("15 jamais une boîte noire", ["questions", "fiche"],
     ["journal_repond_aux_seize_questions", "chaque_rejet_porte_son_motif"]),
]


def auditer() -> int:
    tests = (RACINE / "tests" / "test_radar.py").read_text(encoding="utf-8")
    noms = set(re.findall(r"def (test_\w+)", tests))
    modules = {p.stem for p in (RACINE / "radar").glob("*.py")}

    print(f"{'RÈGLE':<52} {'MODULE':<15} {'TESTS':<7} ÉTAT")
    print("-" * 90)
    trous = []
    for libelle, mods, fragments in REGLES:
        presents = [m for m in mods if m in modules]
        couverts = [f for f in fragments if any(f in t for t in noms)]
        if presents and len(couverts) == len(fragments):
            etat = "✔"
        else:
            etat = "✗ NON COUVERT" if not couverts else f"~ partiel"
            trous.append((libelle, [f for f in fragments if f not in couverts],
                          [m for m in mods if m not in modules]))
        print(f"{libelle:<52} {(presents[0] if presents else '—'):<15} "
              f"{len(couverts)}/{len(fragments):<5} {etat}")

    print()
    if not trous:
        print(f"Les {len(REGLES)} règles du cahier des charges sont tenues par un module")
        print("et par leurs tests de comportement.")
        return 0

    print("RÈGLES NON TENUES :")
    for libelle, fragments, mods in trous:
        if mods:
            print(f"  {libelle} → module(s) absent(s) : {', '.join(mods)}")
        if fragments:
            print(f"  {libelle} → test(s) absent(s) : {', '.join(fragments)}")
    return 1


if __name__ == "__main__":
    sys.exit(auditer())
