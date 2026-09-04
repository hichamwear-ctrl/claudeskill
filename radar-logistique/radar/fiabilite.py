"""FIABILITÉ DE L'INFORMATION — à ne jamais confondre avec la valeur économique.

Deux questions différentes, et les mélanger fait rater des affaires :

    « Combien ça peut rapporter ? »        → score.py
    « À quel point j'en suis sûr ? »       → ce module

Une information peu fiable peut être excellente commercialement. Une phrase
trouvée sur le site d'une PME — « nous cherchons un transporteur pour la
Wallonie » — n'a ni référence officielle, ni date, ni montant. Sa fiabilité est
faible. Sa valeur, elle, peut dépasser celle d'un marché public de 40 pages.

Le radar doit donc la faire remonter HAUT, avec :

    FIABILITÉ : FAIBLE
    ACTION    : VÉRIFIER

et surtout PAS la dévaloriser artificiellement. Dévaloriser l'incertain, c'est
transformer un radar commercial en lecteur de portails officiels — exactement
ce qu'on ne veut pas.

Ce module ne connaît aucune source. Il ne demande jamais « ça vient de TED ? »
mais « qu'est-ce qui est prouvé ? ». Un avis TED sans acheteur publié est moins
fiable qu'une page d'entreprise qui nomme son besoin, sa zone et son contact.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Niveau(Enum):
    FORTE = "FORTE"
    MOYENNE = "MOYENNE"
    FAIBLE = "FAIBLE"
    NULLE = "NULLE"

    @property
    def emoji(self) -> str:
        return {"FORTE": "●●●", "MOYENNE": "●●○", "FAIBLE": "●○○", "NULLE": "○○○"}[self.value]


@dataclass
class Evaluation:
    niveau: Niveau
    motifs: list = field(default_factory=list)     # ce qui est prouvé
    manques: list = field(default_factory=list)    # ce qui ne l'est pas

    def motif(self) -> str:
        bouts = self.motifs + [f"sans {m}" for m in self.manques]
        return " · ".join(bouts[:4]) or "aucun élément d'appréciation"


# Ce qui rend une information vérifiable. Aucun de ces critères ne nomme une
# source : ce sont des propriétés de la DONNÉE, pas de son émetteur.
def evaluer(opp, *, nature=None, lecture=None, collecte=None) -> Evaluation:
    """Note ce qui est PROUVÉ, jamais ce qui est plausible."""
    from .nature import Nature

    points = 0
    motifs, manques = [], []

    # 1. La donnée vient-elle vraiment d'Internet, et l'a-t-on horodatée ?
    if collecte is not None:
        points += 2
        motifs.append(f"collecte prouvée le {str(collecte.collecte_le)[:10]}")
    else:
        manques.append("preuve de collecte")

    # 2. Peut-on retrouver la page ?
    if getattr(opp, "plateforme", None) or getattr(opp, "lien_dossier", None):
        points += 1
        motifs.append("lien vers la source")
    else:
        manques.append("lien vérifiable")

    ref = str(getattr(opp, "ref_source", "") or "")
    if ref and not ref.startswith("SANS-REF-"):
        points += 1
        motifs.append("référence propre à la source")
    else:
        manques.append("référence")

    # 3. Le besoin est-il nommé par quelqu'un ?
    if getattr(opp, "acheteur", None):
        points += 1
        motifs.append("demandeur nommé")
    else:
        manques.append("demandeur nommé")

    # 4. L'information se contredit-elle elle-même ?
    #
    # CE QUI A ÉTÉ RETIRÉ ICI, ET POURQUOI. Ce bloc accordait un ou deux points
    # selon la CONFIANCE dans l'état de procédure : « état démontré », « état
    # probable ». Mesuré en branchant enfin le vocabulaire réel sur le banc
    # d'essai — six formes du MÊME besoin, mêmes preuves — la seule forme
    # publique montait d'un cran de fiabilité. La raison : elle seule publie
    # une rubrique normée qui énonce son propre état. Une page d'entreprise ne
    # peut pas en publier, jamais.
    #
    # C'était donc un point que seules les sources publiques structurées
    # pouvaient gagner : une prime à l'officialité déguisée en mesure de
    # fiabilité. Le module jurait ne nommer aucune source — c'était vrai à la
    # lettre, et faux en substance.
    #
    # Et le critère était de toute façon mal placé : savoir si un dépôt est
    # ouvert est un fait sur la PROCÉDURE, pas sur la véracité du besoin. Il a
    # son champ, sa confiance et ses preuves affichées à part — les compter ici
    # revenait à les compter deux fois.
    #
    # Ce qui RESTE est une vraie propriété de l'information, et n'importe
    # quelle source peut l'avoir : se contredire.
    if lecture is not None and lecture.contradictions:
        points -= 1
        # En tête : quand deux informations se contredisent, c'est la
        # première chose à dire, pas la quatrième.
        manques.insert(0, "cohérence interne")

    # 5. La nature de l'information. Une hypothèse reste une hypothèse — on le
    #    DIT, on ne la punit pas dans le score.
    if nature is Nature.FAIT:
        points += 1
        motifs.append("besoin publié")
    elif nature is Nature.HYPOTHESE:
        points -= 1
        manques.append("confirmation du besoin")

    if points >= 6:
        niveau = Niveau.FORTE
    elif points >= 4:
        niveau = Niveau.MOYENNE
    elif points >= 1:
        niveau = Niveau.FAIBLE
    else:
        niveau = Niveau.NULLE
    return Evaluation(niveau, motifs, manques)
