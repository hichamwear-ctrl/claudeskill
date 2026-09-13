"""Cette page mérite-t-elle d'être surveillée ?

    CANDIDATE  →  (indice fort et explicite)  →  SURVEILLÉE

CE MODULE NE CONTIENT AUCUN VOCABULAIRE MÉTIER. Il n'en invente pas, il n'en
recopie pas. Il pose une question aux deux mécanismes qui existent déjà et qui
sont, eux, les seuls dépositaires du métier :

    Ontologie (config/capacites.yaml)  « ce texte parle-t-il de notre métier ? »
    DetecteurDeRole (config/roles.yaml) « la prestation est-elle l'objet, ou
                                          n'est-elle qu'un accessoire du produit ? »

Construire ici une seconde liste de mots ferait exister deux définitions du
métier qui divergeraient au premier ajout. Il n'y en a qu'une, et elle est en
configuration.

IL FAUT UNE PREUVE POSITIVE. L'INCERTITUDE N'EN EST PAS UNE.
============================================================

Une version antérieure promouvait dès que l'ontologie reconnaissait le métier
et que le rôle n'était PAS « fournisseur ». C'était promouvoir sur l'absence de
contre-preuve : `A_VERIFIER` veut dire « je n'ai pas pu trancher », jamais
« c'est une prestation ». Sur un libellé de trois mots, le détecteur de rôle ne
tranche presque jamais — dix promotions sur onze tenaient donc à un seul mot
générique, le plus souvent parce que le nom de l'entreprise contient lui-même
un mot du métier (« Colis Privé » contient « colis »).

C'est exactement ce que le projet s'interdit :

    la présence d'un mot-clé ne doit jamais promouvoir
    INCERTAIN vaut mieux qu'INCORRECT

Le vocabulaire de DOMAINE est d'ailleurs documenté dans radar/activite.py comme
l'équivalent textuel d'un CPV générique : il confirme qu'on parle de transport,
il ne dit pas DE QUOI. Lui faire porter une promotion, c'est lui faire porter
une décision qu'il n'a pas été conçu à prendre.

QUATRE RÈGLES, DANS CET ORDRE
=============================

    1. l'ontologie ne reconnaît rien              →  AUCUNE   · reste CANDIDATE
    2. rôle FOURNISSEUR — CONTRE-PREUVE           →  MOYENNE  · reste CANDIDATE
    3. une FAMILLE métier, ou un rôle PRESTATAIRE →  FORTE    · PROMUE
       — la preuve positive
    4. domaine générique seul, rôle non tranché   →  MOYENNE  · reste CANDIDATE

Le veto passe AVANT la preuve positive, et ce n'est pas un détail :
« fourniture et livraison de repas en liaison froide » porte la famille
« alimentaire » ET le rôle FOURNISSEUR. Dans l'autre ordre, elle serait promue.

UNE CANDIDATE N'EST JAMAIS SUPPRIMÉE. Ne pas promouvoir, c'est ne pas décider ;
ce n'est pas écarter. Elle garde son URL, ses provenances, sa raison, ses
signaux, son état — et elle reste réévaluable. L'écart, lui, s'écrit avec son
motif, et c'est une décision humaine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .role import Role


class Confiance(Enum):
    FORTE = "FORTE"
    MOYENNE = "MOYENNE"
    AUCUNE = "AUCUNE"


@dataclass
class Pertinence:
    """Le verdict, et de quoi le relire dans six mois."""
    confiance: Confiance
    role: Role = Role.A_VERIFIER
    preuves: list = field(default_factory=list)
    domaine: bool = False            # le vocabulaire de domaine est présent
    familles: list = field(default_factory=list)   # les spécialités reconnues

    @property
    def promouvoir(self) -> bool:
        """Seule une confiance FORTE promeut. Le reste attend."""
        return self.confiance is Confiance.FORTE

    def raison(self) -> str:
        """La raison est CONSERVÉE avec la page : une promotion sans motif
        relisible est une décision qu'on ne pourra pas contester."""
        if self.promouvoir:
            base = (f"PROMUE AUTOMATIQUEMENT — ROLE={self.role.value} — "
                    f"CONFIANCE={self.confiance.value}")
            return base + (f" — {self.preuves[0]}" if self.preuves else "")
        if self.confiance is Confiance.MOYENNE:
            if self.role is Role.FOURNISSEUR:
                return (f"CANDIDATE — À QUALIFIER — ROLE={self.role.value} — "
                        "la prestation paraît accessoire à un achat de fourniture")
            # Le cas le plus fréquent, et le plus important à écrire en clair :
            # on reconnaît le domaine, on n'a AUCUNE preuve positive.
            detail = f" — {self.preuves[0]}" if self.preuves else ""
            return (f"CANDIDATE — À QUALIFIER — ROLE={self.role.value} — "
                    f"domaine reconnu, aucune preuve positive{detail}")
        return "CANDIDATE — À QUALIFIER — aucun rattachement au métier constaté"


def evaluer(texte: str, ontologie, detecteur, *, cpv=None, segments=None,
            blocs=None) -> Pertinence:
    """Interroge les deux mécanismes existants. N'en remplace aucun.

    Aucun des deux n'est modifié, ni contourné, ni pondéré : on lit leur
    réponse telle quelle.
    """
    if not (texte or "").strip():
        return Pertinence(Confiance.AUCUNE)

    # ── 1. Rien ne rattache ce texte au métier ──
    correspondance = ontologie.analyser(texte, cpv=cpv, segments=segments)
    if not correspondance.correspond:
        return Pertinence(Confiance.AUCUNE)

    analyse = detecteur.analyser(texte, cpv=cpv, blocs=blocs)

    # ── 2. LA CONTRE-PREUVE PRIME SUR TOUT ──
    # « Fourniture et livraison de poissons » : l'acheteur veut du poisson. La
    # page parle de livraison sans que la prestation soit l'objet. Ce veto
    # s'applique même quand une famille métier est reconnue par ailleurs.
    if analyse.role is Role.FOURNISSEUR:
        return Pertinence(Confiance.MOYENNE, analyse.role,
                          list(analyse.contre_preuves), domaine=True,
                          familles=list(correspondance.familles))

    # ── 3. LA PREUVE POSITIVE — et elle seule promeut ──
    # Une FAMILLE nomme une spécialité du métier ; un rôle PRESTATAIRE établit
    # que la prestation EST l'objet. L'une ou l'autre suffit ; aucune des deux
    # ne se déduit d'un silence.
    if correspondance.familles:
        preuves = [f"famille « {f} »" for f in correspondance.familles]
        preuves += [f"« {t} »" for termes in correspondance.preuves.values()
                    for t in termes[:1]]
        return Pertinence(Confiance.FORTE, analyse.role, preuves, domaine=True,
                          familles=list(correspondance.familles))
    if analyse.role is Role.PRESTATAIRE:
        return Pertinence(Confiance.FORTE, analyse.role, list(analyse.preuves),
                          domaine=True)

    # ── 4. Le domaine seul : on est dans le transport, on ne sait pas de quoi ──
    return Pertinence(Confiance.MOYENNE, analyse.role,
                      [correspondance.preuve_domaine] if correspondance.preuve_domaine
                      else [], domaine=True)
