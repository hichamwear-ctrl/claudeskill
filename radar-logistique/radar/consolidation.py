"""UNE ADRESSE, PLUSIEURS LECTURES — une seule fiche à l'écran.

    la base garde deux avis          l'exploitant voit une adresse

La clé d'un avis est (source, référence), et elle le reste : c'est elle qui
permet de savoir QUI a montré quoi, donc de mesurer l'apport propre de chaque
moteur. Une même URL vue par un moteur puis relue sur la page collectée porte
donc DEUX avis, et c'est correct — les deux lectures sont réelles et datées.

Ce que l'exploitant voyait, lui, c'était deux fois la même entreprise, avec
deux verdicts opposés et deux actions contradictoires :

    🟢 DIRECT                    45   FAIT        CONTACTER L'ENTREPRISE
    ⚪ PAS ENCORE UNE OPPORTUNITÉ 24   HYPOTHÈSE   CLASSER SANS SUITE

CE MODULE NE DÉCIDE RIEN, N'ÉCRIT RIEN, NE SUPPRIME RIEN
========================================================

C'est une VUE. Il reçoit des lignes déjà lues en base et rend la même
information regroupée. Il ne touche ni aux avis, ni aux verdicts, ni aux
provenances, ni aux scores, ni au comptage par moteur — rien de ce qui se
mesure ne passe par ici.

L'ORDRE EST DÉTERMINISTE, ET IL RÉUTILISE L'AXE QUI EXISTE
==========================================================

Aucun nouveau score de preuve n'est inventé. La hiérarchie est celle de
`radar/fiabilite.py`, déjà validée et déjà écrite sur chaque opportunité :

    FORTE  ●●●   >   MOYENNE ●●○   >   FAIBLE ●○○   >   NULLE ○○○

Cet axe range exactement ce qu'on veut ranger, et pour les bonnes raisons :
il accorde ses points à la preuve de collecte, au lien vérifiable, au
demandeur nommé et au besoin publié. Une page réellement lue les réunit ;
un titre de résultat de moteur n'en réunit presque aucun. La hiérarchie
demandée — page lue, puis extrait, puis titre et métadonnées, puis titre
seul — en découle sans qu'on ait à la déclarer une deuxième fois.

À fiabilité égale, on départage par le score, puis par la lecture la plus
RÉCENTE. Jamais par le nom de la source : le radar ne classe pas ses
informations selon qui les lui a montrées.

LA CONTRADICTION EST UNE INFORMATION — ELLE S'AFFICHE
=====================================================

Quand deux lectures d'une même adresse ne donnent pas la même catégorie, on
ne choisit pas en silence. La fiche principale est la mieux étayée, et la
divergence est écrite avec la preuve de chaque lecture. Elle dit quelque
chose d'utile : le titre ne suffisait pas, la page le disait.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .pages import normaliser

# L'axe de radar/fiabilite.py, lu tel quel. Aucune valeur n'est inventée ici :
# ce sont les quatre niveaux du module, dans leur ordre.
_RANG_PREUVE = {"FORTE": 3, "MOYENNE": 2, "FAIBLE": 1, "NULLE": 0}

DIVERGENCE = "⚠️ LECTURES DIVERGENTES"


def _valeur(ligne, cle, defaut=None):
    """Lire une colonne, que la ligne soit un Row sqlite ou un dict."""
    try:
        v = ligne[cle]
    except (KeyError, IndexError, TypeError):
        return defaut
    return defaut if v is None else v


def _rang(ligne) -> tuple:
    """Le plus étayé d'abord : niveau de preuve, puis score. Tous deux
    décroissants. La date se traite à part, par un tri préalable — voir
    `grouper` : elle est croissante en texte et doit être décroissante ici."""
    return (-_RANG_PREUVE.get(str(_valeur(ligne, "fiabilite", "")), -1),
            -int(_valeur(ligne, "score", 0) or 0))


def _quand(ligne) -> str:
    return str(_valeur(ligne, "derniere_vue", "") or "")


@dataclass
class Adresse:
    """Une URL, et toutes les lectures qu'on en a — la mieux étayée en tête."""
    url: str
    lectures: list = field(default_factory=list)

    @property
    def principale(self):
        return self.lectures[0]

    @property
    def autres(self) -> list:
        return self.lectures[1:]

    @property
    def divergentes(self) -> bool:
        """Deux lectures qui ne classent pas la même adresse pareil."""
        return len({str(_valeur(l, "type", "")) for l in self.lectures}) > 1

    def preuve_de(self, ligne) -> str:
        """DE QUOI cette lecture tire ce qu'elle dit — jamais « d'où »."""
        niveau = str(_valeur(ligne, "fiabilite", "") or "NON MESURÉE")
        return f"preuve {niveau}"


def grouper(lignes) -> list[Adresse]:
    """Regroupe des lignes déjà lues par ADRESSE, sans rien recalculer.

    L'ordre des adresses est celui d'arrivée — donc celui de la requête, qui
    trie déjà par score. Une adresse prend le rang de sa meilleure lecture ;
    regrouper ne fait jamais remonter ni descendre une affaire.
    """
    index: dict = {}
    ordre: list = []
    for ligne in lignes or []:
        url = normaliser(str(_valeur(ligne, "ref_source", "") or ""))
        if url not in index:
            index[url] = Adresse(url)
            ordre.append(url)
        index[url].lectures.append(ligne)
    for url in ordre:
        # Deux tris, et le tri de Python est STABLE : la date la plus récente
        # départage d'abord, puis la preuve et le score reprennent la main.
        # À preuve et score égaux, il reste donc la lecture la plus récente —
        # « une lecture plus récente peut être plus fiable qu'une ancienne ».
        index[url].lectures.sort(key=_quand, reverse=True)
        index[url].lectures.sort(key=_rang)
    return [index[u] for u in ordre]


def bloc_divergence(adresse: Adresse, *, fiche) -> list[str]:
    """Les lectures écartées de la fiche principale, écrites en clair.

    `fiche` rend la ligne d'en-tête d'une lecture : on la reçoit plutôt que
    de la reconstruire, pour que la mise en forme reste au même endroit.
    """
    if not adresse.autres:
        return []
    L = []
    if adresse.divergentes:
        L.append(f"     {DIVERGENCE}")
        L.append("     Les deux lectures sont réelles et datées. Ce désaccord")
        L.append("     dit ce qui a été lu, et ce qui ne l'avait pas été.")
    else:
        L.append(f"     AUTRE(S) LECTURE(S) — {len(adresse.autres)}")
    L.append(f"     · lecture principale : {fiche(adresse.principale)}"
             f"   ({adresse.preuve_de(adresse.principale)})")
    for l in adresse.autres:
        L.append(f"     · autre lecture     : {fiche(l)}"
                 f"   ({adresse.preuve_de(l)})")
        L.append(f"       source {_valeur(l, 'source_avis', _valeur(l, 'source', '?'))}"
                 f"   ·   vue le {str(_valeur(l, 'derniere_vue', '') or 'DATE INCONNUE')[:10]}")
    return L
