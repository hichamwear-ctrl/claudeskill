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
    statut_source: str | None = None
    type_information: str | None = None

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
                    pays_livraison=list(opp.pays_livraison),
                    statut_source=opp.statut_source,
                    type_information=opp.type_information)]

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
            pays_livraison=lot.pays_livraison or list(opp.pays_livraison),
            # Le statut du LOT prime sur celui du marché parent : c'est tout
            # l'intérêt d'éclater. Un marché « attribué » dont le lot 3 est
            # encore ouvert doit produire trois situations distinctes.
            statut_source=lot.statut_source or opp.statut_source,
            type_information=lot.type_information or opp.type_information))
    return sortie


def eclater(opp) -> list:
    """CHANGEMENT : un marché à plusieurs lots produit une opportunité PAR LOT.

    Chaque lot obtient sa propre référence, son propre montant, sa propre
    échéance et sera analysé, classé et noté seul. Le lien vers le marché parent
    est conservé — c'est lui qui évite de compter deux fois le même besoin.
    """
    import copy

    if not opp.lots:
        return [opp]

    sortie = []
    for lot in lots_de(opp):
        enfant = copy.copy(opp)
        enfant.lots = []                       # un lot ne se re-découpe pas
        enfant.marche_ref = opp.ref_source
        enfant.lot_numero = lot.numero
        enfant.ref_source = f"{opp.ref_source}#L{lot.numero}"
        enfant.intitule = lot.libelle
        enfant.texte = lot.texte
        enfant.cpv = lot.cpv
        enfant.exigences = lot.exigences
        enfant.pays_collecte = lot.pays_collecte
        enfant.pays_livraison = lot.pays_livraison
        # Un lot sans montant propre n'HÉRITE PAS de celui du marché : ce serait
        # inventer une valeur. Il reste NON PUBLIÉ.
        enfant.montant = lot.montant
        enfant.duree_mois = lot.duree_mois
        enfant.statut_source = lot.statut_source
        enfant.type_information = lot.type_information
        enfant.provenances = list(opp.provenances)
        sortie.append(enfant)
    return sortie
