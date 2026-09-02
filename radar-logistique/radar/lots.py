"""Analyse LOT PAR LOT.

Ne jamais rejeter un marché entier parce que son titre général paraît
incompatible. Un marché « Fourniture, livraison et installation d'équipements »
peut contenir en lot 15 un « déménagement de postes de soudure » parfaitement
exécutable.

Le marché est retenu dès qu'UN lot est compatible, et la notification nomme
lesquels.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Lot:
    numero: str
    intitule: str
    texte: str = ""
    cpv: list[str] = field(default_factory=list)
    montant: float | None = None
    duree_mois: int | None = None
    exigences: dict = field(default_factory=dict)
    pays_collecte: list[str] = field(default_factory=list)
    pays_livraison: list[str] = field(default_factory=list)

    @property
    def libelle(self) -> str:
        return f"LOT {self.numero} — {self.intitule}" if self.numero else self.intitule


def lots_de(opp) -> list[Lot]:
    """Les lots d'une opportunité. Un marché sans lot déclaré en a un : lui-même.

    Chaque lot HÉRITE de ce que le marché porte et que le lot ne précise pas :
    un lot ne redéclare presque jamais la géographie ni les exigences générales.
    """
    if not opp.lots:
        return [Lot(numero="", intitule=opp.intitule, texte=opp.texte, cpv=list(opp.cpv),
                    montant=opp.montant, duree_mois=opp.duree_mois,
                    exigences=dict(opp.exigences or {}),
                    pays_collecte=list(opp.pays_collecte),
                    pays_livraison=list(opp.pays_livraison))]

    sortie = []
    for lot in opp.lots:
        herite = dict(opp.exigences or {})
        herite.update(lot.exigences or {})
        sortie.append(Lot(
            numero=lot.numero,
            intitule=lot.intitule,
            # Le texte du marché reste utile au lot : il porte souvent le contexte.
            texte=f"{lot.texte} {opp.texte}".strip(),
            cpv=lot.cpv or list(opp.cpv),
            montant=lot.montant if lot.montant is not None else None,
            duree_mois=lot.duree_mois if lot.duree_mois is not None else opp.duree_mois,
            exigences=herite,
            pays_collecte=lot.pays_collecte or list(opp.pays_collecte),
            pays_livraison=lot.pays_livraison or list(opp.pays_livraison)))
    return sortie
