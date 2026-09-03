#!/usr/bin/env python3
"""LE RADAR, toutes sources confondues — la démonstration de l'architecture.

Le centre du radar n'est pas la source. Ce n'est pas non plus l'appel d'offres.
C'est le BESOIN COMMERCIAL et sa RENTABILITÉ.

Ce script le prouve en faisant entrer, dans le MÊME moteur et le même rapport,
huit formes de besoin qui n'ont rien en commun dans leur format :

    marché européen · marché belge · résultat de moteur de recherche ·
    page d'entreprise · signal d'emploi · signal d'implantation ·
    tournée de bourse de fret · marché attribué · métier nouveau

Aucune n'est « secondaire ». Aucune n'est privilégiée. Chacune est un capteur ;
le cerveau est ailleurs — compréhension du besoin, faisabilité, économie.

    python3 outils/radar_commercial.py

Ces fixtures sont des DONNÉES DE DÉMONSTRATION. Elles ne portent pas de preuve
de collecte : en mode RÉEL, elles seraient toutes refusées.
"""

from __future__ import annotations

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

# (fichier de fixtures, adaptateur à utiliser). Un même adaptateur peut servir
# plusieurs fichiers : ce qui change, c'est le BESOIN, pas le lecteur.
LOTS = [
    ("ted.json",           "ted"),
    ("attribution.json",   "ted"),
    ("bda.json",           "bda"),
    ("google.json",        "google"),
    ("entreprise.json",    "entreprise"),
    ("nouveau-metier.json", "entreprise"),
    ("signaux.json",       "signaux"),
    ("bourse_fret.json",   "bourse_fret"),
    ("portail.json",       "portail"),
]


def _cfg(nom):
    return yaml.safe_load((RACINE / nom).read_text(encoding="utf-8"))


def vocabulaires() -> dict:
    """Le vocabulaire de procédure déclaré par chaque adaptateur."""
    from radar.procedure import Vocabulaire
    sortie = {}
    for chemin in sorted((RACINE / "sources").glob("*.yaml")):
        cfg = yaml.safe_load(chemin.read_text(encoding="utf-8")) or {}
        sortie[cfg.get("source", chemin.stem)] = Vocabulaire(cfg)
    return sortie


def _moteur() -> Moteur:
    return Moteur(_cfg("profil.yaml"), _cfg("config/capacites.yaml"),
                  _cfg("config/geographie.yaml"), _cfg("config/ponderations.yaml"),
                  _cfg("config/roles.yaml"), vocabulaires=vocabulaires())


def charger(fichier: str, source: str) -> list:
    cfg = _cfg(f"sources/{source}.yaml")
    ad = Adaptateur.depuis_config(cfg)
    charges = json.loads((RACINE / "exemples" / "sources" / fichier).read_text(
        encoding="utf-8"))
    defauts = {"signal": cfg.get("signal"), "secteur": cfg.get("secteur_par_defaut")}
    return [vers_opportunite(ad, c, source, defauts) for c in charges]


def principal(argv=None) -> int:
    cx = ouvrir(":memory:")
    moteur = _moteur()
    total = 0
    for fichier, source in LOTS:
        opportunites = charger(fichier, source)
        total += len(opportunites)
        traiter(cx, moteur, opportunites, mode=Mode.DEMO)

    r = rapport_mod.construire(
        cx, Mode.DEMO, limite_top=20,
        cible=_cfg("profil.yaml").get("cible_economique", {}),
        proche_km=_cfg("config/ponderations.yaml").get("effort", {}).get(
            "distance_depot_confortable_km", 50))
    print(r.en_texte(avec_fiches=False))
    print()
    print(f"{total} besoins entrés par {len({s for _, s in LOTS})} formats différents, "
          f"un seul moteur, un seul rapport.")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
