#!/usr/bin/env python3
"""LES DOUZE FAMILLES DE BESOIN — le catalogue d'essai du radar commercial.

Un appel d'offres public est UNE forme de besoin. Pas la forme de référence.

Ce module déclare douze familles, publiques ET privées, chacune lue par
l'adaptateur qui sait la lire. Elles servent au banc d'essai, au rapport de
démonstration et aux tests d'indépendance — et le partage n'est pas décoratif :
il permet de lancer le radar sur le privé seul, sur le public seul, ou sur les
deux, et de vérifier que le résultat reste cohérent dans les trois cas.

    python3 outils/familles.py            # ce que chaque famille produit
    python3 outils/familles.py --prive    # le radar sans aucune source publique
    python3 outils/familles.py --public   # le radar sans aucune source privée
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

import yaml                                                    # noqa: E402

from radar.adaptateur import Adaptateur, vers_opportunite      # noqa: E402
from radar.base import ouvrir                                  # noqa: E402
from radar.chaine import Moteur, traiter                       # noqa: E402
from radar.mode import Mode                                    # noqa: E402
from radar import rapport as rapport_mod                       # noqa: E402

# (famille, fichier, adaptateur, secteur)
#
# `secteur` dit d'où vient le besoin — public ou privé — et sert UNIQUEMENT à
# composer des lots d'essai. Il n'entre jamais dans le moteur : le score, la
# capacité et la classification ne le voient pas.
FAMILLES = [
    ("besoin_prive",           "besoin_prive.json",           "entreprise",  "prive"),
    ("besoin_public",          "besoin_public.json",          "bda",         "public"),
    ("sous_traitance",         "sous_traitance.json",         "entreprise",  "prive"),
    ("partenariat",            "partenariat.json",            "entreprise",  "prive"),
    ("entreprise_a_demarcher", "entreprise_a_demarcher.json", "entreprise",  "prive"),
    ("signal_economique",      "signal_economique.json",      "signaux",     "prive"),
    ("emploi_signal",          "emploi_signal.json",          "signaux",     "prive"),
    ("attribution",            "attribution.json",            "ted",         "public"),
    ("preinformation",         "preinformation.json",         "portail",     "public"),
    ("appel_offres",           "appel_offres.json",           "ted",         "public"),
    ("lot",                    "lot.json",                    "bda",         "public"),
    ("metier_inconnu",         "metier_inconnu.json",         "entreprise",  "prive"),
    # La treizième famille n'est pas une opportunité — et c'est pour ça
    # qu'elle manquait. Ajoutée après avoir mesuré une VRAIE page : douze
    # familles décrivaient douze façons de gagner de l'argent, aucune ne
    # décrivait une page qu'on lit et qui ne donne rien.
    ("pas_encore_une_opportunite", "pas_encore_une_opportunite.json",
                                                                "page_web",    "prive"),
]

PRIVEES = {f for f, _, _, s in FAMILLES if s == "prive"}
PUBLIQUES = {f for f, _, _, s in FAMILLES if s == "public"}


def _cfg(nom):
    return yaml.safe_load((RACINE / nom).read_text(encoding="utf-8"))


def vocabulaires() -> dict:
    from radar.procedure import Vocabulaire
    sortie = {}
    for chemin in sorted((RACINE / "sources").glob("*.yaml")):
        cfg = yaml.safe_load(chemin.read_text(encoding="utf-8")) or {}
        sortie[cfg.get("source", chemin.stem)] = Vocabulaire(cfg)
    return sortie


def moteur() -> Moteur:
    return Moteur(_cfg("profil.yaml"), _cfg("config/capacites.yaml"),
                  _cfg("config/geographie.yaml"), _cfg("config/ponderations.yaml"),
                  _cfg("config/roles.yaml"), vocabulaires=vocabulaires())


def charger(famille: str) -> list:
    """Les opportunités d'une famille, lues par son adaptateur déclaré."""
    _, fichier, source, _ = next(f for f in FAMILLES if f[0] == famille)
    cfg = _cfg(f"sources/{source}.yaml")
    ad = Adaptateur.depuis_config(cfg)
    charges = json.loads((RACINE / "exemples" / "familles" / fichier).read_text(
        encoding="utf-8"))
    defauts = {"signal": cfg.get("signal"), "secteur": cfg.get("secteur_par_defaut")}
    return [vers_opportunite(ad, c, c.get("fournisseur") or source, defauts)
            for c in charges]


def toutes(familles=None) -> list:
    noms = familles if familles is not None else [f[0] for f in FAMILLES]
    sortie = []
    for nom in noms:
        sortie += charger(nom)
    return sortie


def passer(familles=None, mode: Mode = Mode.DEMO):
    cx = ouvrir(":memory:")
    b = traiter(cx, moteur(), toutes(familles), mode=mode)
    return cx, b


def principal(argv=None) -> int:
    p = argparse.ArgumentParser(description="Le radar sur ses douze familles de besoin")
    p.add_argument("--prive", action="store_true", help="aucune source publique")
    p.add_argument("--public", action="store_true", help="aucune source privée")
    a = p.parse_args(argv)

    if a.prive:
        noms, titre = sorted(PRIVEES), "SANS AUCUNE SOURCE PUBLIQUE"
    elif a.public:
        noms, titre = sorted(PUBLIQUES), "SANS AUCUNE SOURCE PRIVÉE"
    else:
        noms, titre = [f[0] for f in FAMILLES], "LES DOUZE FAMILLES"

    cx, b = passer(noms)
    print(f"╔{'═' * 68}╗")
    print(f"║  {titre:<66}║")
    print(f"╚{'═' * 68}╝\n")
    print(f"{len(noms)} famille(s) · {b.lus} besoin(s) lus · "
          f"{b.capter} CAPTER · {b.developper} DÉVELOPPER · {b.rejet} rejet(s)")
    print(f"réconciliation : écart {b.livre.ecart()}\n")

    for l in cx.execute(
            "SELECT o.score, o.score_mesurable, o.type, o.moteur, o.action,"
            " o.nature, o.etat_procedure,"
            " o.intitule, a.source FROM opportunites o JOIN avis a ON a.id = o.avis_id"
            " WHERE o.type <> 'REJET' ORDER BY o.score DESC"):
        # « — » quand rien d'économique n'a été observé : un nombre affiché
        # prétend être une mesure, et se compare à celui d'à côté.
        note = l["score"] if l["score_mesurable"] else "—"
        print(f"  [{note:>3}] {(l['intitule'] or '')[:40]:<42}"
              f"{l['type'][:12]:<13}{(l['nature'] or '?')[:9]:<10}"
              f"{(l['action'] or '?')[:22]:<24}{l['source']}")

    r = rapport_mod.construire(cx, Mode.DEMO,
                               cible=_cfg("profil.yaml").get("cible_economique", {}))
    print()
    for nom, liste in (("CAPTER", r.capter), ("DÉVELOPPER", r.developper),
                       ("SIGNAUX", r.signaux), ("À VÉRIFIER", r.a_verifier_liste)):
        print(f"  {nom:<14} {len(liste)}")
    return 0 if b.livre.ecart() == 0 else 1


if __name__ == "__main__":
    sys.exit(principal())
