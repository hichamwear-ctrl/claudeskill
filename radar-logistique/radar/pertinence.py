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

LE VETO EST À DEUX NIVEAUX — il ne porte plus sur le seul vocabulaire
=====================================================================

La version précédente refusait à la porte tout texte que l'ontologie ne
reconnaissait pas :

    if not correspondance.correspond:
        return Pertinence(Confiance.AUCUNE)

Ce veto punissait une entreprise pour ses MOTS, pas pour l'absence d'affaire :

    « Nous recherchons un partenaire pour acheminer chaque jour nos
      commandes vers nos douze magasins. »

— un besoin parfaitement explicite, écrit sans un seul terme de notre
ontologie — ressortait AUCUNE, donc la page n'était jamais promue, donc
jamais lue, donc jamais analysée. Le faux négatif était invisible : il ne
laissait aucune trace, puisque rien n'était entré en base.

Le vocabulaire métier est désormais UN indice parmi six, et non plus la
condition d'entrée. Ce qui ouvre la porte, c'est l'ANCRAGE COMMERCIAL, dont
la définition unique vit dans radar/ancrage.py :

    vocabulaire · besoin · événement · date · chiffre · exigence

QUATRE RÈGLES, DANS CET ORDRE
=============================

    1. AUCUN des six signaux d'ancrage             →  AUCUNE   · reste CANDIDATE
    2. rôle FOURNISSEUR — CONTRE-PREUVE            →  MOYENNE  · reste CANDIDATE
    3. un BESOIN ÉNONCÉ, ou un rôle PRESTATAIRE    →  FORTE    · PROMUE
       — la preuve positive
    4. ancrée, sans preuve positive                →  MOYENNE  · reste CANDIDATE

Le veto passe AVANT la preuve positive, et ce n'est pas un détail :
« fourniture et livraison de repas en liaison froide » porte la famille
« alimentaire » ET le rôle FOURNISSEUR. Dans l'autre ordre, elle serait promue.

LE VOCABULAIRE N'EST PLUS UNE PREUVE POSITIVE
=============================================

La règle 3 lisait auparavant `correspondance.familles` : reconnaître une
spécialité du métier suffisait à promouvoir. Mesuré sur une page réelle,
cela donnait :

    « Spécialiste du transport et de la logistique en Belgique depuis 1998 »
                                                          →  FORTE, PROMUE

Une page vitrine, qui ne demande rien à personne, entrait en surveillance
parce qu'elle nommait notre métier. C'est le symétrique exact du défaut
corrigé plus haut, et le projet s'interdit les deux :

    la présence d'un mot-clé ne doit jamais promouvoir
    l'absence de nos mots ne doit jamais empêcher de découvrir

Promeut désormais ce qui DEMANDE : un besoin énoncé par celui qui l'a, ou un
rôle PRESTATAIRE établi — c'est-à-dire la prestation reconnue comme l'objet.

UNE INVITATION N'EST PAS UNE DEMANDE
====================================

`nature.besoin_enonce_dans` est lu ici plutôt que `besoin_exprime_dans`, et
la différence est commerciale : « Rejoignez-nous », « Become part of our
team », « Wanted » sont écrits par n'importe quelle entreprise de n'importe
quel secteur. Les promouvoir ferait entrer en surveillance toutes les pages
de recrutement du web. Elles restent CANDIDATE — donc relisibles, donc
jamais perdues — sans être promues pour autant.

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
    # LES SIGNAUX D'ANCRAGE trouvés dans ce texte — conservés pour qu'une
    # porte ouverte, ou fermée, se relise dans six mois sans rejouer la page.
    signaux: list = field(default_factory=list)

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
            ancre = (f" — ancrage : {' · '.join(self.signaux)}"
                     if self.signaux else "")
            # « domaine reconnu » se dit quand il l'est, et se tait sinon :
            # une page ancrée par une date seule ne parle pas de notre métier,
            # et l'écrire serait faux.
            quoi = ("domaine reconnu, aucune preuve positive" if self.domaine
                    else "aucune preuve positive")
            return (f"CANDIDATE — À QUALIFIER — ROLE={self.role.value} — "
                    f"{quoi}{detail}{ancre}")
        return ("CANDIDATE — À QUALIFIER — aucun ancrage commercial observé : "
                "ni métier nommé, ni besoin, ni événement, ni date, ni "
                "chiffre, ni exigence")


def evaluer(texte: str, ontologie, detecteur, *, cpv=None, segments=None,
            blocs=None) -> Pertinence:
    """Interroge les deux mécanismes existants. N'en remplace aucun.

    Aucun des deux n'est modifié, ni contourné, ni pondéré : on lit leur
    réponse telle quelle.
    """
    if not (texte or "").strip():
        return Pertinence(Confiance.AUCUNE)

    from . import ancrage as mod_ancrage
    from . import nature as nat

    correspondance = ontologie.analyser(texte, cpv=cpv, segments=segments)
    metier = bool(correspondance.correspond)

    # ── 1. AUCUN ANCRAGE — ni métier, ni besoin, ni date, ni chiffre… ──
    # Le veto ne porte plus sur le seul vocabulaire : une page peut écrire son
    # besoin dans des mots que nous n'avions pas prévus, et elle doit pouvoir
    # entrer. Ce qui reste dehors, c'est ce qui ne porte AUCUNE prise.
    ancre = mod_ancrage.depuis_texte(texte, vocabulaire=metier)
    if not ancre.ancre:
        return Pertinence(Confiance.AUCUNE)

    analyse = detecteur.analyser(texte, cpv=cpv, blocs=blocs)
    familles = list(correspondance.familles)

    # ── 2. LA CONTRE-PREUVE PRIME SUR TOUT ──
    # « Fourniture et livraison de poissons » : l'acheteur veut du poisson. La
    # page parle de livraison sans que la prestation soit l'objet. Ce veto
    # s'applique même quand une famille métier est reconnue par ailleurs.
    if analyse.role is Role.FOURNISSEUR:
        return Pertinence(Confiance.MOYENNE, analyse.role,
                          list(analyse.contre_preuves), domaine=metier,
                          familles=familles, signaux=list(ancre.signaux))

    # ── 3. LA PREUVE POSITIVE — et elle seule promeut ──
    # DEMANDER, ou ÊTRE la prestation. Nommer le métier n'est ni l'un ni
    # l'autre : une page vitrine nomme le métier et ne demande rien.
    if nat.besoin_enonce_dans(texte):
        preuves = ["un besoin est énoncé dans ce texte"]
        preuves += [f"famille « {f} »" for f in familles]
        return Pertinence(Confiance.FORTE, analyse.role, preuves,
                          domaine=metier, familles=familles,
                          signaux=list(ancre.signaux))
    if analyse.role is Role.PRESTATAIRE:
        return Pertinence(Confiance.FORTE, analyse.role, list(analyse.preuves),
                          domaine=metier, familles=familles,
                          signaux=list(ancre.signaux))

    # ── 4. Ancrée, sans preuve positive : on lira peut-être, on ne promeut pas ──
    preuves = [f"famille « {f} »" for f in familles]
    if not preuves and correspondance.preuve_domaine:
        preuves = [correspondance.preuve_domaine]
    return Pertinence(Confiance.MOYENNE, analyse.role, preuves,
                      domaine=metier, familles=familles,
                      signaux=list(ancre.signaux))
