"""L'ANCRAGE COMMERCIAL — y a-t-il ici le moindre FAIT exploitable ?

    « ça parle de mon métier »   ≠   « il y a une affaire ici »

Ces deux questions étaient confondues à deux endroits du radar, et elles s'y
trompaient de deux façons OPPOSÉES :

    radar/pertinence.py   le vocabulaire métier était NÉCESSAIRE — une page
                          qui écrivait son besoin dans d'autres mots était
                          refusée à la porte, donc jamais lue ;
    radar/chaine.py       le vocabulaire métier était SUFFISANT — une famille
                          reconnue dans un titre nu suffisait à écrire
                          « CONTACTER L'ENTREPRISE ».

Ce module porte LA définition unique de ce qui ancre un texte dans le
commerce. Elle tient en six signaux :

    VOCABULAIRE   le métier est nommé
    BESOIN        quelqu'un écrit qu'il cherche quelque chose
    EVENEMENT     un fait observable s'est produit chez quelqu'un d'autre
    DATE          une échéance, un démarrage
    CHIFFRE       un montant, un volume, une cadence, une durée
    EXIGENCE      une condition posée

DEUX ENTRÉES, UNE SEULE LISTE DE SIGNAUX
========================================

    depuis_texte(...)          pour LA PORTE DES PAGES   (radar/pertinence.py)
    depuis_opportunite(...)    pour LA CHAÎNE            (radar/chaine.py)

Les deux cherchent les mêmes six signaux. Elles ne disposent pas des mêmes
PREUVES, et c'est la seule différence :

    · à la porte, on n'a qu'un texte — on lit donc des FORMES (une date
      s'écrit comme une date dans tous les métiers, un montant aussi) ;
    · dans la chaîne, l'adaptateur a déjà extrait des CHAMPS — on lit donc
      `opp.echeance_brute`, `opp.montant`, `opp.exigences`, qui sont plus
      sûrs qu'une expression régulière et qui restent ce qu'ils étaient
      avant ce module.

Ne PAS faire lire des formes à la chaîne est délibéré : le titre réel
« Sous Traitant Transport : plus de 50 emplois (18 février 2026) | Indeed »
porte une date et un nombre, et n'a jamais annoncé le moindre besoin.

CE MODULE N'A PAS DE VOCABULAIRE MÉTIER, ET N'EN AURA JAMAIS
============================================================

Il n'en contient aucun et n'en définit aucun. Il POSE LA QUESTION aux
dépositaires existants et lit leur réponse :

    le métier          → Ontologie (config/capacites.yaml), via l'appelant
    le besoin          → radar/nature.py, listes BESOIN_DIRECT
    l'événement        → radar/nature.py, liste EVENEMENT_OBSERVABLE

Ce qu'il définit en propre — et rien d'autre — ce sont trois FORMES, qui ne
désignent aucun métier et ne pourraient pas en désigner un :

    une date s'écrit comme une date ;
    une quantité est un nombre suivi d'une unité ou d'une cadence ;
    une exigence est une grammaire — « requis », « obligatoire », « vereist ».

Y ajouter un jour « palette », « tournée » ou « colis » ferait exactement ce
que ce module existe pour empêcher : une deuxième ontologie, cachée ici,
qui divergerait de la vraie au premier ajout.

DEUX LECTURES DU MÊME RÉSULTAT
==============================

    .ancre        au moins un signal, vocabulaire compris.
                  C'est LA PORTE : on accepte de lire la page.

    .commercial   au moins un signal AUTRE que le vocabulaire.
                  C'est L'AFFAIRE : reconnaître le métier dit qu'on parle de
                  transport, jamais qu'il y a quelque chose à vendre.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .activite import normaliser

VOCABULAIRE = "vocabulaire métier"
BESOIN = "besoin exprimé"
EVENEMENT = "événement observable"
DATE = "date"
CHIFFRE = "chiffre ou volume"
EXIGENCE = "exigence"

# L'ordre de lecture des signaux : du plus explicite au plus circonstanciel.
# Il ne pondère rien — il rend seulement la raison affichée stable d'un
# passage à l'autre.
ORDRE = (BESOIN, EVENEMENT, EXIGENCE, CHIFFRE, DATE, VOCABULAIRE)


# ── LES TROIS FORMES ──────────────────────────────────────────────────────
#
# Aucune ne nomme un métier. Un mois s'appelle « mars » chez un transporteur
# comme chez un boulanger ; « requis » n'est pas plus logistique que juridique.

_MOIS = ("janvier|fevrier|mars|avril|mai|juin|juillet|aout|septembre|octobre"
         "|novembre|decembre"
         "|januari|februari|maart|april|mei|juni|juli|augustus|september"
         "|oktober|november|december"
         "|january|february|march|may|june|july|august")

_DATE = re.compile(
    r"\b\d{1,2} \d{1,2} \d{2,4}\b"              # 15 03 2026 — la ponctuation
    r"|\b\d{4} \d{1,2} \d{1,2}\b"               # a été aplatie en espaces
    rf"|\b\d{{1,2}} (?:{_MOIS})\b"
    rf"|\b(?:{_MOIS}) \d{{4}}\b"
    r"|\b(?:a partir du|des le|des la|au plus tard le|date limite"
    r"|uiterlijk|vanaf|deadline|starting)\b")

# Une quantité est un NOMBRE suivi d'une unité de mesure, d'une monnaie ou
# d'une cadence. « 12 tournées » ne compte pas ici : « tournée » est du métier,
# et le métier a déjà son signal. « 12 par semaine » compte : c'est une forme.
# « palettes » a figuré ici une première fois, et le test d'absence de
# vocabulaire métier l'a refusé — à juste titre : une palette est une unité DU
# TRANSPORT, sa place est dans config/capacites.yaml. Ne restent que des
# unités qu'un boulanger emploierait dans les mêmes termes.
_UNITES = r"eur|euros?|k eur|m eur|km|kg|tonnes?|m2|m3|litres?|pourcent|%"
_CADENCES = (r"par jour|par semaine|par mois|par an|par annee"
             r"|chaque jour|chaque semaine|chaque mois"
             r"|quotidien(?:ne|nes|s)?|hebdomadaire|mensuel(?:le|les|s)?"
             r"|per dag|per week|per maand|per day|per week|per month")
_CHIFFRE = re.compile(
    rf"\b\d[\d ]* (?:{_UNITES})\b"
    rf"|\b\d[\d ]* [a-z]+ (?:{_CADENCES})\b"
    rf"|\b\d[\d ]* (?:{_CADENCES})\b"
    r"|\b\d[\d ]* (?:fois|maal|times) par\b")

# La GRAMMAIRE d'une condition posée. Elle dit qu'on exige quelque chose ;
# elle ne dit jamais quoi.
_EXIGENCE = re.compile(
    r"\b(?:exige|exigee|exigees|exiges|exigence|exigences"
    r"|requis|requise|requises|requiert"
    r"|obligatoire|obligatoires|indispensable|indispensables"
    r"|prerequis|conditions requises|conditions d acces"
    r"|il faut disposer|vous devez disposer|vous devez etre|doit disposer"
    r"|vereist|verplicht|voorwaarden"
    r"|required|mandatory|must have|requirements"
    r"|erforderlich|voraussetzung)\b")


@dataclass
class Ancrage:
    """Ce qui a été trouvé, et rien d'autre. Aucun poids, aucun seuil."""
    signaux: list[str] = field(default_factory=list)

    @property
    def ancre(self) -> bool:
        """LA PORTE — au moins un signal, vocabulaire compris."""
        return bool(self.signaux)

    @property
    def hors_vocabulaire(self) -> list[str]:
        return [s for s in self.signaux if s != VOCABULAIRE]

    @property
    def commercial(self) -> bool:
        """L'AFFAIRE — au moins un signal AUTRE que le vocabulaire.

        Reconnaître « transport routier » dit que la page parle de notre
        métier. Ça ne dit pas qu'il y a une affaire à y prendre.
        """
        return bool(self.hors_vocabulaire)

    def raison(self) -> str:
        if not self.signaux:
            return "aucun ancrage commercial observé"
        return " · ".join(self.signaux)


def _ranger(trouves: set) -> Ancrage:
    return Ancrage([s for s in ORDRE if s in trouves])


def depuis_texte(texte, *, vocabulaire: bool = False) -> Ancrage:
    """L'ancrage LISIBLE DANS UN TEXTE — la porte des pages.

    `vocabulaire` est la réponse de l'ontologie, posée par l'appelant : ce
    module ne connaît pas le métier et n'a pas à le connaître.
    """
    from . import nature as nat
    plat = normaliser(texte or "")
    trouves = set()
    if vocabulaire:
        trouves.add(VOCABULAIRE)
    if nat.besoin_exprime_dans(texte):
        trouves.add(BESOIN)
    if nat.evenement_observable_dans(texte):
        trouves.add(EVENEMENT)
    if _DATE.search(plat):
        trouves.add(DATE)
    if _CHIFFRE.search(plat):
        trouves.add(CHIFFRE)
    if _EXIGENCE.search(plat):
        trouves.add(EXIGENCE)
    return _ranger(trouves)


def depuis_opportunite(opp, *, vocabulaire: bool = False, nature=None,
                       procedure_detectee: bool = False) -> Ancrage:
    """L'ancrage porté par les CHAMPS d'une opportunité — la chaîne.

    Exactement les faits que `radar/chaine.py` lisait déjà avant l'existence
    de ce module, à une exception près, décidée et mesurée : la FAMILLE
    métier n'est plus comptée comme un ancrage commercial. Elle reste un
    signal — `.ancre` la voit — mais `.commercial` ne la voit plus.
    """
    from .nature import Nature
    trouves = set()
    if vocabulaire:
        trouves.add(VOCABULAIRE)
    if getattr(opp, "est_signal", False):
        trouves.add(EVENEMENT)
    if nature is not None and nature is not Nature.HYPOTHESE:
        trouves.add(BESOIN)
    if opp.echeance_brute or opp.date_demarrage:
        trouves.add(DATE)
    if (opp.montant or opp.cadence or opp.duree_mois or opp.km_annuels
            or opp.vehicules_requis or opp.chauffeurs_requis
            or (opp.lots and len(opp.lots) > 1)):
        trouves.add(CHIFFRE)
    if opp.exigences or opp.exigences_texte:
        trouves.add(EXIGENCE)
    if procedure_detectee:
        # Une procédure détectée est un fait déjà reconnu ailleurs : un
        # guichet, un dépôt, un état. On le lit, on ne le recalcule pas.
        trouves.add(EVENEMENT)
    return _ranger(trouves)
