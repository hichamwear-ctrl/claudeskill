#!/usr/bin/env python3
"""MESURE RÉELLE — famille C, moteur de recherche.

Ingère les résultats RÉELS conservés dans validation/collectes_reelles/, et
seulement eux : titre verbatim et URL verbatim. Le résumé en prose que l'outil
de recherche produit par-dessus est écrit par un modèle — ce n'est pas une
observation, il n'entre pas.

    python3 outils/mesure_famille_c.py [--inscrire]

`--inscrire` écrit au registre réel. Sans lui, l'outil affiche seulement.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

import yaml                                                     # noqa: E402

from radar import validation as val                             # noqa: E402
from radar.adaptateur import Adaptateur, vers_opportunite       # noqa: E402
from radar.base import ouvrir                                   # noqa: E402
from radar.chaine import Moteur, traiter                        # noqa: E402
from radar.classification import Type                           # noqa: E402
from radar.mode import Mode, estampiller                        # noqa: E402
from radar.procedure import Vocabulaire                         # noqa: E402

BRUT = RACINE / "validation" / "collectes_reelles" / "2026-09-05-recherche-brut.json"


def _cfg(nom):
    return yaml.safe_load((RACINE / nom).read_text(encoding="utf-8"))


def _moteur():
    voc = {(c := _cfg(f"sources/{f.name}")).get("source", f.stem): Vocabulaire(c)
           for f in sorted((RACINE / "sources").glob("*.yaml"))}
    return Moteur(_cfg("profil.yaml"), _cfg("config/capacites.yaml"),
                  _cfg("config/geographie.yaml"), _cfg("config/ponderations.yaml"),
                  _cfg("config/roles.yaml"), vocabulaires=voc)


def charger() -> tuple[list, str]:
    octets = BRUT.read_bytes()
    empreinte = hashlib.sha256(octets).hexdigest()
    donnees = json.loads(octets)
    cfg = _cfg("sources/recherche.yaml")
    ad = Adaptateur.depuis_config(cfg)
    sortie = []
    for bloc in donnees["requetes"]:
        for r in bloc["resultats"]:
            # SEULS le titre et l'URL. Rien d'autre n'a été observé.
            charge = estampiller({"titre": r["title"], "url": r["url"]},
                                 source="recherche", reference=r["url"])
            sortie.append(vers_opportunite(
                ad, charge, "recherche",
                {"secteur": cfg.get("secteur_par_defaut"),
                 "consulte_le": donnees["collecte_le"], "requete": bloc["requete"]}))
    return sortie, empreinte


def principal(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--inscrire", action="store_true",
                   help="écrire au registre des mesures réelles")
    a = p.parse_args(argv)

    opportunites, empreinte = charger()
    cx = ouvrir(":memory:")
    m = _moteur()
    # Mode RÉEL : chaque ligne doit porter sa preuve de collecte.
    bilan = traiter(cx, m, opportunites, mode=Mode.REEL)

    print(Mode.REEL.bandeau())
    print()
    print("═" * 74)
    print("  FAMILLE C — MOTEUR DE RECHERCHE · DONNÉE RÉELLE")
    print("═" * 74)
    print(f"  brut conservé : validation/collectes_reelles/{BRUT.name}")
    print(f"  sha256        : {empreinte}")
    print(f"  ingéré        : titre et URL verbatim, rien d'autre")
    print(f"  entrées       : {len(opportunites)} · retenues {bilan.lus} "
          f"· doublons {bilan.doublons}")
    print()

    resultats = [(o, m.analyser(o)) for o in opportunites]
    par_type = {}
    for o, r in resultats:
        par_type.setdefault(r.classement.type, []).append((o, r))

    for typ in sorted(par_type, key=lambda t: t.value):
        lignes = par_type[typ]
        print(f"  {typ.emoji} {typ.value}   ({len(lignes)})")
        for o, r in lignes:
            note = r.score.total if r.score.mesurable else "—"
            print(f"     [{note:>3}] {o.intitule[:56]}")
            print(f"           {o.plateforme[:64]}")
            print(f"           nature {r.nature.value} · état "
                  f"{r.lecture.etat_affiche} · {r.classement.action.value}")
        print()

    print("─" * 74)
    qualifiees = [x for x in resultats if x[1].classement.type.notifiable]
    chiffrees = [x for x in qualifiees if x[1].priorite.ca_mesurable]
    print(f"  OPPORTUNITÉS QUALIFIÉES  : {len(qualifiees)} / {len(resultats)}")
    print(f"  DONT CHIFFRÉES           : {len(chiffrees)}")
    print(f"  CA IDENTIFIÉ             : "
          f"{sum(x[1].priorite.rang_ca for x in chiffrees):,.0f} €/an"
          .replace(",", " "))

    if a.inscrire:
        val.inscrire(val.Mesure(
            horodatage="2026-09-05T00:00:00+00:00", famille="recherche",
            origine="outil de recherche web ; titres et URL verbatim, "
                    "résumé en prose exclu ; brut conservé et haché",
            reference=f"{len(opportunites)} résultats réels, 2 requêtes",
            empreinte=empreinte, page_conservee=BRUT.name,
            completude="extrait de listing",
            verdict=f"{len(qualifiees)} qualifiée(s) sur {len(resultats)}",
            porte_un_besoin=bool(qualifiees),
            ca_identifie=sum(x[1].priorite.rang_ca for x in chiffrees)))
        print()
        print("  Mesure inscrite au registre réel.")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
