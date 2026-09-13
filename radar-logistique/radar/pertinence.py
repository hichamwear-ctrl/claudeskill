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

TROIS NIVEAUX, ET LA PRUDENCE VA DANS LE BON SENS
=================================================

    FORTE    le texte parle du métier ET la prestation n'est pas un simple
             accessoire d'un achat de produit  →  promotion automatique
    MOYENNE  le texte parle du métier, mais c'est un achat de FOURNITURE :
             la livraison y est accessoire  →  reste CANDIDATE
    AUCUNE   rien ne rattache ce texte au métier  →  reste CANDIDATE

« Partenaires », « Actualités », « Nous rejoindre », « Mentions légales » ne
rattachent rien : ils restent candidats. C'est voulu — un mot générique n'est
pas un indice.

UNE CANDIDATE N'EST JAMAIS SUPPRIMÉE. Ne pas promouvoir, c'est ne pas décider ;
ce n'est pas écarter. L'écart, lui, s'écrit avec son motif.
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
    domaine: bool = False

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
            return (f"CANDIDATE — À QUALIFIER — ROLE={self.role.value} — "
                    "la prestation paraît accessoire à un achat de fourniture")
        return "CANDIDATE — À QUALIFIER — aucun rattachement au métier constaté"


def evaluer(texte: str, ontologie, detecteur, *, cpv=None, segments=None,
            blocs=None) -> Pertinence:
    """Interroge les deux mécanismes existants. N'en remplace aucun.

    Aucun des deux n'est modifié, ni contourné, ni pondéré : on lit leur
    réponse telle quelle.
    """
    if not (texte or "").strip():
        return Pertinence(Confiance.AUCUNE)

    correspondance = ontologie.analyser(texte, cpv=cpv, segments=segments)
    if not correspondance.correspond:
        return Pertinence(Confiance.AUCUNE)

    analyse = detecteur.analyser(texte, cpv=cpv, blocs=blocs)
    if analyse.role is Role.FOURNISSEUR:
        # « Fourniture et livraison de poissons » : l'acheteur veut du poisson.
        # La page parle de livraison sans que la prestation soit l'objet.
        return Pertinence(Confiance.MOYENNE, analyse.role,
                          list(analyse.contre_preuves), domaine=True)
    return Pertinence(Confiance.FORTE, analyse.role, list(analyse.preuves),
                      domaine=True)
