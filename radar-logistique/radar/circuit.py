"""Par quel CHEMIN cette opportunité est-elle arrivée ?

Deux circuits, et ils ne se confondent jamais :

    SOURCE_CONNUE      nous savions déjà où regarder — un portail déclaré, une
                       entreprise au registre, une page surveillée, une
                       attribution, un signal. Aucun moteur de recherche n'est
                       nécessaire, et l'indisponibilité de Google n'y change
                       rien.

    SOURCE_DÉCOUVERTE  un moteur de recherche nous a montré quelque chose que
                       nous ne connaissions pas. C'est ce qui fait entrer de
                       NOUVELLES entreprises dans le registre.

CE QUE LE CIRCUIT NE FAIT JAMAIS
================================

Il n'entre PAS dans le score. Pas un point, pas un bonus, pas un malus.

    Même opportunité, mêmes données commerciales → même score.

Le circuit sert à la provenance, à la traçabilité, au diagnostic et aux
métriques de rendement. Il dit d'où vient l'information, jamais ce qu'elle
vaut. Une affaire trouvée en revisitant une page connue et la même affaire
trouvée par Google valent exactement pareil — parce que c'est le BESOIN qui a
une valeur, pas le chemin qui nous y a menés.

Une opportunité peut porter LES DEUX circuits : le même besoin vu au BDA puis
retrouvé par un moteur garde ses deux provenances et ses deux circuits.
"""

from __future__ import annotations

CONNUE = "SOURCE_CONNUE"
DECOUVERTE = "SOURCE_DÉCOUVERTE"

CIRCUITS = (CONNUE, DECOUVERTE)

# Par défaut, une source est CONNUE : un adaptateur de fichier, un portail
# déclaré, une page surveillée. Seule la découverte web doit se déclarer.
DEFAUT = CONNUE


def lire(valeur) -> str:
    """Un circuit illisible ne devient pas DÉCOUVERTE : on retombe sur le
    défaut, qui n'affirme rien de plus que ce qu'on sait."""
    v = str(valeur or "").strip().upper().replace("É", "É")
    for c in CIRCUITS:
        if v == c:
            return c
    return DEFAUT


def de_provenances(provenances) -> list[str]:
    """Les circuits réellement portés par une opportunité, sans doublon et
    dans un ordre stable."""
    vus = []
    for p in provenances or []:
        d = p if isinstance(p, dict) else getattr(p, "__dict__", {})
        c = d.get("circuit")
        if c and c not in vus:
            vus.append(c)
    return vus


def libelle(provenances) -> str:
    circuits = de_provenances(provenances)
    return " + ".join(circuits) if circuits else "NON RENSEIGNÉ"
