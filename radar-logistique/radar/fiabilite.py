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

    # 4. L'état de la procédure est-il démontré ?
    if lecture is not None:
        from .procedure import Confiance
        if lecture.confiance is Confiance.ELEVEE:
            points += 2
            motifs.append("état démontré")
        elif lecture.confiance is Confiance.MOYENNE:
            points += 1
            motifs.append("état probable")
        else:
            manques.append("état démontrable")
        if lecture.contradictions:
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
