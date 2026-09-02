"""Registre des sources — l'honnêteté du radar tient ici.

Une source n'est JAMAIS présentée comme consultée sans une trace horodatée.
L'état par défaut est JAMAIS_CONSULTEE, et rien ne le change à part une
consultation réelle.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class Etat(Enum):
    JAMAIS_CONSULTEE = "JAMAIS CONSULTÉE"
    ACTIVE = "ACTIVE"
    ERREUR = "ERREUR"
    NON_DISPONIBLE = "NON DISPONIBLE"
    DESACTIVEE = "DÉSACTIVÉE"


# Cycle de vie d'une source découverte par le niveau 1.
class Cycle(Enum):
    DECOUVERTE = "DÉCOUVERTE"
    A_EVALUER = "À ÉVALUER"
    SURVEILLEE = "SURVEILLÉE"
    ECARTEE = "ÉCARTÉE"


@dataclass
class Rendement:
    """Ce qu'une source produit RÉELLEMENT. C'est ça qui fixe sa priorité —
    pas sa notoriété. TED n'a aucun droit acquis."""
    lues: int = 0
    retenues: int = 0
    direct: int = 0
    renforcement: int = 0
    a_construire: int = 0
    prospect: int = 0
    contacts: int = 0
    contrats: int = 0

    @property
    def taux_utile(self) -> float:
        return self.retenues / self.lues if self.lues else 0.0

    def priorite(self) -> float:
        """Rendement observé. Une source non consultée ne peut pas se classer :
        elle renvoie None, pas un zéro qui la ferait passer pour mauvaise."""
        if not self.lues:
            return None
        # Un contrat pèse plus qu'un contact, un contact plus qu'une fiche.
        return (self.retenues + 3 * self.contacts + 10 * self.contrats) / self.lues


@dataclass
class Source:
    nom: str
    famille: str
    methode: str                      # api | navigation | fichier | moteur_recherche
    etat: Etat = Etat.JAMAIS_CONSULTEE
    cycle: Cycle | None = None
    derniere_consultation: str | None = None
    derniere_erreur: str | None = None
    rendement: Rendement = field(default_factory=Rendement)
    requetes: list[str] = field(default_factory=list)
    motif_indisponible: str | None = None

    def consultee(self, resultats: int):
        self.etat = Etat.ACTIVE
        self.derniere_consultation = datetime.now(timezone.utc).isoformat(timespec="seconds")
        self.derniere_erreur = None
        self.rendement.lues += resultats

    def en_erreur(self, message: str):
        self.etat = Etat.ERREUR
        self.derniere_consultation = datetime.now(timezone.utc).isoformat(timespec="seconds")
        self.derniere_erreur = message

    def indisponible(self, motif: str):
        """Ni consultée, ni en erreur : hors service pour une raison connue —
        clé absente, abonnement absent, conditions d'utilisation contraires."""
        self.etat = Etat.NON_DISPONIBLE
        self.motif_indisponible = motif

    def ligne(self) -> str:
        quand = self.derniere_consultation or "—"
        p = self.rendement.priorite()
        prio = f"{p:.2f}" if p is not None else "n/d"
        detail = f" · {self.motif_indisponible}" if self.motif_indisponible else ""
        return (f"{self.nom:<22} {self.etat.value:<17} {quand[:19]:<20} "
                f"lues={self.rendement.lues:<6} retenues={self.rendement.retenues:<5} "
                f"prio={prio}{detail}")


class Registre:
    def __init__(self):
        self.sources: dict[str, Source] = {}

    def declarer(self, nom, famille, methode) -> Source:
        if nom not in self.sources:
            self.sources[nom] = Source(nom=nom, famille=famille, methode=methode)
        return self.sources[nom]

    def par_priorite(self) -> list[Source]:
        """Les sources jamais consultées restent en fin de liste, sans être
        jugées : on ne peut pas classer ce qu'on n'a pas mesuré."""
        mesurees = [s for s in self.sources.values() if s.rendement.priorite() is not None]
        inconnues = [s for s in self.sources.values() if s.rendement.priorite() is None]
        mesurees.sort(key=lambda s: -s.rendement.priorite())
        return mesurees + inconnues

    def rapport(self) -> str:
        L = ["REGISTRE DES SOURCES", "=" * 100, ""]
        for s in self.par_priorite():
            L.append("  " + s.ligne())
        jamais = sum(1 for s in self.sources.values() if s.etat is Etat.JAMAIS_CONSULTEE)
        L.append("")
        L.append(f"  {jamais} source(s) sur {len(self.sources)} n'ont JAMAIS été consultées.")
        if jamais:
            L.append("  Aucun chiffre de marché ne peut en être tiré.")
        return "\n".join(L)
