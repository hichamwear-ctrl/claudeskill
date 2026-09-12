#!/usr/bin/env python3
"""MESURE RÉELLE — famille D, portail de marchés publics.

La question : un TITRE de listing suffit-il à faire conclure un état de
procédure que seul le contenu de l'avis peut justifier ?

Ingère les résultats réels conservés dans validation/collectes_reelles/ :
titre verbatim et URL verbatim, rien d'autre. Aucune page individuelle n'a été
lue — le réseau sortant est fermé.

    python3 outils/mesure_famille_d.py [--inscrire]
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
from radar.chaine import Moteur                                 # noqa: E402
from radar.mode import estampiller                              # noqa: E402
from radar.procedure import Vocabulaire                         # noqa: E402

BRUT = RACINE / "validation" / "collectes_reelles" / "2026-09-12-portail-brut.json"

# Les états AFFIRMÉS : ceux qu'un titre seul ne doit jamais produire.
AFFIRMES = ("POSTULABLE", "ATTRIBUÉ", "FERMÉ", "ANNULÉ", "INFRUCTUEUX", "ANNONCÉ")


def _cfg(nom):
    return yaml.safe_load((RACINE / nom).read_text(encoding="utf-8"))


def _moteur():
    voc = {(c := _cfg(f"sources/{f.name}")).get("source", f.stem): Vocabulaire(c)
           for f in sorted((RACINE / "sources").glob("*.yaml"))}
    return Moteur(_cfg("profil.yaml"), _cfg("config/capacites.yaml"),
                  _cfg("config/geographie.yaml"), _cfg("config/ponderations.yaml"),
                  _cfg("config/roles.yaml"), vocabulaires=voc)


def charger():
    octets = BRUT.read_bytes()
    donnees = json.loads(octets)
    # L'adaptateur « portail » : c'est bien la famille D qu'on mesure.
    cfg = _cfg("sources/portail.yaml")
    ad = Adaptateur.depuis_config(cfg)
    sortie = []
    for bloc in donnees["requetes"]:
        for r in bloc["resultats"]:
            charge = estampiller({"intitule": r["title"], "url": r["url"]},
                                 source="portail", reference=r["url"])
            o = vers_opportunite(ad, charge, "portail",
                                 {"secteur": cfg.get("secteur_par_defaut"),
                                  "consulte_le": donnees["collecte_le"],
                                  "requete": bloc["requete"]})
            sortie.append((r["_forme"], o))
    return sortie, hashlib.sha256(octets).hexdigest()


def principal(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--inscrire", action="store_true")
    a = p.parse_args(argv)

    entrees, empreinte = charger()
    m = _moteur()

    print("═" * 78)
    print("  FAMILLE D — PORTAIL DE MARCHÉS PUBLICS · DONNÉE RÉELLE")
    print("═" * 78)
    print(f"  brut     : validation/collectes_reelles/{BRUT.name}")
    print(f"  sha256   : {empreinte}")
    print(f"  ingéré   : titre et URL verbatim — AUCUNE page individuelle lue")
    print(f"  entrées  : {len(entrees)}")
    print()
    print("  OBSERVÉ = le titre, tel quel.  INTERPRÉTÉ = ce que le moteur")
    print("  en conclut.  DÉDUIT = ce qu'il calcule ensuite.")
    print()

    etats_affirmes, resultats = [], []
    for forme, o in entrees:
        r = m.analyser(o)
        resultats.append((forme, o, r))
        etat = r.lecture.etat_affiche
        marque = "❌" if etat in AFFIRMES else "  "
        if etat in AFFIRMES:
            etats_affirmes.append((o.intitule, etat, r.lecture.preuves))
        print(f"  {marque} [{forme:<20}] {o.intitule[:52]}")
        print(f"       INTERPRÉTÉ  état {etat} · nature {r.nature.value}")
        if r.lecture.preuves:
            for pr in r.lecture.preuves:
                print(f"                   preuve rang {pr.rang} : « {pr.observation} »")
        ca = r.ca.ligne()
        print(f"       DÉDUIT      {r.classement.type.emoji} {r.classement.type.value}"
              f" · {r.classement.action.value}")
        print(f"                   CA {ca}")
        print()

    # ── COMPTEURS DEMANDÉS ────────────────────────────────────────────────
    pages_lues = 0            # aucune page individuelle n'est accessible
    qualifiables = [x for x in resultats
                    if x[2].lecture.etat_affiche in AFFIRMES
                    and x[2].lecture.confiance.value in ("élevée", "moyenne")]
    inconnus = [x for x in resultats if x[2].lecture.etat_affiche == "INCONNU"]
    hors = [x for x in resultats if x[2].lecture.etat_affiche == "HORS PROCÉDURE"]
    lots = sum(len(x[1].lots) for x in resultats if len(x[1].lots) > 1)
    ca_mesurable = [x for x in resultats if x[2].priorite.ca_mesurable]

    print("─" * 78)
    print("  MESURES SÉPARÉES")
    print(f"    pages réellement observées          : {pages_lues}"
          "   (réseau fermé — aucune page individuelle lue)")
    print(f"    procédures réellement qualifiables  : {len(qualifiables)}")
    print(f"    états INCONNU                       : {len(inconnus)}")
    print(f"    états HORS PROCÉDURE                : {len(hors)}")
    print(f"    états AFFIRMÉS depuis un titre seul : {len(etats_affirmes)}")
    print(f"    lots observables                    : {lots}")
    print(f"    CA réellement mesurable             : {len(ca_mesurable)} "
          f"({'0 €' if not ca_mesurable else '?'})")
    print()

    if etats_affirmes:
        print("  ❌ ÉTATS AFFIRMÉS SANS PREUVE INDIVIDUELLE")
        for titre, etat, preuves in etats_affirmes:
            print(f"     {etat:<12} ← « {titre[:56]} »")
            for pr in preuves:
                print(f"                  rang {pr.rang} : {pr.observation}")
    else:
        print("  ✅ AUCUN état affirmé depuis un titre seul.")

    if a.inscrire:
        val.inscrire(val.Mesure(
            horodatage="2026-09-12T00:00:00+00:00", famille="marche_public",
            origine="outil de recherche web ; titres et URL verbatim ; aucune "
                    "page individuelle lue (réseau fermé) ; brut conservé et haché",
            reference=f"{len(entrees)} résultats réels, 2 requêtes",
            empreinte=empreinte, page_conservee=BRUT.name,
            completude="extrait de listing",
            verdict=f"{len(etats_affirmes)} état(s) affirmé(s) depuis un titre ; "
                    f"{len(ca_mesurable)} CA mesurable",
            porte_un_besoin=bool([x for x in resultats
                                  if x[2].classement.type.notifiable]),
            ca_identifie=0.0))
        print("\n  Mesure inscrite au registre réel.")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
