"""NIVEAU 1 — découverte Internet.

Google ne cherche pas des appels d'offres : il cherche des BESOINS. Les requêtes
sont générées par croisement modèle × prestation × zone × langue, pas écrites à
la main — sinon la liste serait figée et ne pourrait pas apprendre.

Le connecteur est enfichable. Sans clé, il répond NON DISPONIBLE et ne simule
rien : aucune recherche fictive, aucun résultat inventé. Le scraping des pages
de résultats est exclu — c'est contraire aux conditions d'utilisation.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

POINT_ACCES = "https://www.googleapis.com/customsearch/v1"


@dataclass
class Requete:
    texte: str
    famille: str
    zone: str
    langue: str
    poids: float
    # Rendement observé — alimenté par l'usage, jamais supposé.
    lancee: int = 0
    resultats: int = 0
    retenues: int = 0
    contacts: int = 0
    contrats: int = 0

    @property
    def cle(self) -> str:
        return self.texte

    def rendement(self) -> float | None:
        if not self.lancee:
            return None
        return (self.retenues + 3 * self.contacts + 10 * self.contrats) / self.lancee

    def priorite(self) -> float:
        """Rendement observé s'il existe, poids déclaré sinon. Une requête neuve
        n'est ni favorisée ni pénalisée : elle est simplement non mesurée."""
        r = self.rendement()
        return r * 10 if r is not None else self.poids


class Generateur:
    """Produit les requêtes à partir de la configuration. Rien n'est codé en dur."""

    def __init__(self, config: dict):
        self.cfg = config
        self.langues = config.get("langues", ["fr"])

    def _zones(self):
        return sorted(self.cfg.get("zones", []), key=lambda z: -z.get("poids", 0))

    def generer(self, limite: int | None = None) -> list[Requete]:
        sorties: list[Requete] = []
        prestations = self.cfg.get("prestations", [])
        secteurs = self.cfg.get("secteurs", [])

        for famille, bloc in self.cfg.get("modeles", {}).items():
            poids_famille = bloc.get("poids", 5)
            if famille == "entreprise_ciblee":
                continue                        # déclenché plus tard, par entité
            for langue in self.langues:
                for modele in bloc.get(langue, []):
                    for zone in self._zones():
                        base = modele.replace("{zone}", zone["nom"])
                        poids = poids_famille + zone.get("poids", 0) / 10
                        if "{prestation}" in base:
                            for p in prestations:
                                sorties.append(Requete(base.replace("{prestation}", p),
                                                       famille, zone["nom"], langue, poids))
                        elif "{secteur}" in base:
                            for s in secteurs:
                                sorties.append(Requete(base.replace("{secteur}", s),
                                                       famille, zone["nom"], langue, poids))
                        else:
                            sorties.append(Requete(base, famille, zone["nom"], langue, poids))

        # Déduplication : le même croisement peut naître deux fois.
        vues, uniques = set(), []
        for r in sorties:
            if r.cle not in vues:
                vues.add(r.cle)
                uniques.append(r)
        uniques.sort(key=lambda r: -r.priorite())
        return uniques[:limite] if limite else uniques

    def pour_entreprise(self, entreprise: str, domaine: str | None = None) -> list[Requete]:
        """Deuxième phase : une entreprise découverte devient une cible de
        recherche. C'est ce qui transforme une liste d'URL en graphe de besoins."""
        bloc = self.cfg.get("modeles", {}).get("entreprise_ciblee", {})
        poids = bloc.get("poids", 8)
        sorties = []
        for langue in self.langues:
            for modele in bloc.get(langue, []):
                if "{domaine}" in modele and not domaine:
                    continue
                texte = modele.replace("{entreprise}", entreprise)
                if domaine:
                    texte = texte.replace("{domaine}", domaine)
                sorties.append(Requete(texte, "entreprise_ciblee", entreprise, langue, poids))
        return sorties


# ────────────────────────────────────── moteurs de recherche : voir le module
# radar/moteurs_recherche.py. La découverte ne connaît AUCUN moteur en
# particulier : elle reçoit un objet qui sait « rechercher », et c'est tout.

from .moteurs_recherche import (  # noqa: E402
    Brave, Google, RechercheIndisponible, Registre as RegistreMoteurs, Resultat,
    depuis_environnement,
)

# Noms conservés pour ne rien casser en amont.
ConnecteurIndisponible = RechercheIndisponible
ConnecteurGoogle = Google


def charger_connecteur(env: dict | None = None):
    """Le premier moteur disponible, ou Google (indisponible) pour qu'on
    puisse toujours lire son motif d'indisponibilité."""
    registre = depuis_environnement(env)
    return registre.disponible() or registre.moteurs[0]
