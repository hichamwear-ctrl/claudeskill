#!/usr/bin/env python3
"""LE RADAR TROUVE-T-IL L'ARGENT, ET SAIT-IL PAR QUOI COMMENCER ?

Pas « sait-il traiter huit sources ». Sept affaires volontairement
contradictoires, et une décision qui doit se lire ligne par ligne.

    python3 outils/audit_valeur.py
"""

from __future__ import annotations

import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

import yaml                                                     # noqa: E402

from radar.chaine import Moteur                                 # noqa: E402
from radar.modele import Opportunite                            # noqa: E402
from radar.procedure import Vocabulaire                         # noqa: E402


def _cfg(nom):
    return yaml.safe_load((RACINE / nom).read_text(encoding="utf-8"))


def _moteur():
    voc = {(c := _cfg(f"sources/{f.name}")).get("source", f.stem): Vocabulaire(c)
           for f in sorted((RACINE / "sources").glob("*.yaml"))}
    return Moteur(_cfg("profil.yaml"), _cfg("config/capacites.yaml"),
                  _cfg("config/geographie.yaml"), _cfg("config/ponderations.yaml"),
                  _cfg("config/roles.yaml"), vocabulaires=voc)


METIER = "Transport de marchandises et distribution régionale de colis."


def sept_affaires() -> list:
    """Sept cas qui doivent se départager. Aucun n'est un cas d'école."""
    def o(**kw):
        base = dict(texte=METIER, acheteur="Client", pays_livraison=["BE"],
                    cadence="quotidienne", secteur_acheteur="prive",
                    source="entreprise")
        base.update(kw)
        return Opportunite(**base)

    return [
        ("petite affaire, parfaitement adaptée", o(
            ref_source="1", intitule="Tournée locale de colis",
            montant=54000, duree_mois=12, distance_depot_km=8,
            exigences={"vehicules_min": 2}, vehicules_requis=2, chauffeurs_requis=2)),
        ("grosse affaire, moyennement adaptée", o(
            ref_source="2", intitule="Distribution multi-sites",
            montant=360000, duree_mois=12, distance_depot_km=90,
            exigences={"vehicules_min": 9}, vehicules_requis=9, chauffeurs_requis=9)),
        ("énorme affaire, difficile à exécuter", o(
            ref_source="3", intitule="Logistique nationale",
            montant=1200000, duree_mois=12, distance_depot_km=140,
            exigences={"vehicules_min": 22}, vehicules_requis=22, chauffeurs_requis=20)),
        ("affaire privée non chiffrée, prometteuse", o(
            ref_source="4", intitule="Nous recherchons un transporteur",
            texte="Nous recherchons un transporteur pour nos tournées régionales "
                  "quotidiennes au départ de Bruxelles.",
            acheteur="Delhaize", distance_depot_km=12)),
        ("marché public chiffré", o(
            ref_source="5", source="bda", secteur_acheteur="public",
            intitule="Distribution de colis communaux", type_avis="avis de marché",
            cpv=["60000000"], lien_depot="https://exemple.be/depot",
            montant=216000, duree_mois=24, distance_depot_km=25,
            exigences={"vehicules_min": 4}, vehicules_requis=4, chauffeurs_requis=4)),
        ("signal privé", o(
            ref_source="6", source="signaux", est_signal=True,
            signal_code="recrutement_massif",
            intitule="Recrutement de 15 chauffeurs livreurs à Gand",
            texte="L'entreprise recrute quinze chauffeurs livreurs pour la région "
                  "de Gand.", acheteur="Colruyt")),
        ("renouvellement à venir", o(
            ref_source="7", source="portail", secteur_acheteur="public",
            intitule="Préinformation — externalisation de la logistique",
            type_information="avis de préinformation",
            texte="Le marché actuel de transport arrive à échéance. Une nouvelle "
                  "consultation sera lancée. " + METIER,
            montant=240000, duree_mois=12, distance_depot_km=30)),
    ]


def principal(argv=None) -> int:
    m = _moteur()
    resultats = [(nom, opp, m.analyser(opp)) for nom, opp in sept_affaires()]

    print("╔" + "═" * 70 + "╗")
    print("║  " + "PAR QUOI COMMENCER, ET POURQUOI".ljust(68) + "║")
    print("╚" + "═" * 70 + "╝")
    print()
    print("  Sept affaires. Le classement se fait EN DEUX TEMPS : d'abord ce")
    print("  qui est attaquable aujourd'hui, ensuite ce qui demande un renfort,")
    print("  enfin ce qu'on ne peut pas encore chiffrer. À l'intérieur de chaque")
    print("  groupe, c'est le POTENTIEL qui classe — pas l'adéquation, qui ne")
    print("  bouge plus au-delà de 25 000 €/mois.")
    print()

    def groupe(r):
        """Trois groupes, dans l'ordre où on agit. Trier les sept ensemble
        mettrait une affaire impossible à exécuter en tête de liste."""
        if not r.priorite.ca_mesurable:
            return "3. À QUALIFIER — le CA se demande, il ne se lit pas"
        if r.bilan.bloquants:
            return "2. À DÉVELOPPER — rentable, mais pas seul en l'état"
        if r.classement.moteur.value == "DEVELOPPER":
            return "2. À DÉVELOPPER — rentable, mais pas seul en l'état"
        return "1. ATTAQUABLE MAINTENANT"

    par_groupe = {}
    for nom, opp, r in resultats:
        par_groupe.setdefault(groupe(r), []).append((nom, opp, r))

    for titre in sorted(par_groupe):
        print(f"  {titre}")
        print("  " + "─" * 68)
        for nom, opp, r in sorted(par_groupe[titre],
                                  key=lambda x: x[2].priorite.cle_de_tri):
            annuel = (f"{r.priorite.rang_ca:,.0f} €/an".replace(",", " ")
                      if r.priorite.ca_mesurable else "NON MESURABLE")
            print(f"    {annuel:>16}   adéquation [{r.score.total:>3}]   {nom}")
            print(f"      {opp.intitule[:60]}")
            print(f"      NATURE    {r.nature.value}   ·   ÉTAT  "
                  f"{r.lecture.etat_affiche}")
            print(f"      ACTION    {r.classement.action.value}")
            print(f"      POURQUOI  {r.priorite.ligne()}")
            if r.bilan.bloquants:
                print(f"      MANQUE    {r.bilan.bloquants[0][:56]}")
                for ligne in r.bilan.plan_de_faisabilite()[:3]:
                    print(f"                → {ligne[:54]}")
            if not r.priorite.ca_mesurable:
                print("      QUESTION  quel volume, quelle fréquence, quel budget ?")
            print()

    print("─" * 72)
    print("CE QUE CE CLASSEMENT DIT, ET CE QU'IL NE DIT PAS")
    print()
    print("  Il dit : parmi les affaires chiffrées et attaquables, laquelle")
    print("  rapporte le plus, à quel coût de capacité, et ce qu'il manque.")
    print()
    print("  Il ne dit PAS laquelle sera gagnée. Aucune de ces sept n'a été")
    print("  observée dans le monde réel : ce sont des cas construits pour")
    print("  éprouver la décision, pas des affaires.")
    print()
    from radar.validation import etat
    e = etat()
    print(f"  OPPORTUNITÉS COMMERCIALES RÉELLES OBSERVÉES : {e.opportunites_testees()}")
    print(f"  CONTRATS GAGNÉS                             : NON MESURÉ")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
