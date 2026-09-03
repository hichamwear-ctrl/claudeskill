"""Le livre de comptes — aucune opportunité ne disparaît en silence.

Sept opportunités s'étaient évaporées à cause d'un identifiant vide. Le bug est
corrigé, mais la classe de bug demeure : quelque part entre l'entrée et la
sortie, une ligne peut se perdre sans que personne ne le voie.

Ce module compte à chaque étage et EXIGE que les totaux se réconcilient. Si la
somme ne tombe pas juste, le cycle échoue — il ne continue pas.
"""

from __future__ import annotations

from dataclasses import dataclass, field


class ReconciliationImpossible(Exception):
    """Des lignes ont disparu sans motif. Le cycle s'arrête."""


@dataclass
class Livre:
    brutes: int = 0
    illisibles: dict = field(default_factory=dict)      # motif -> nombre
    normalisees: int = 0
    lots_ajoutes: int = 0
    doublons_certains: int = 0
    doublons_probables: int = 0
    doublons_possibles: int = 0                          # reliés, PAS fusionnés
    rejets: dict = field(default_factory=dict)           # motif -> nombre
    capter: int = 0
    developper: int = 0

    # --------------------------------------------------------- écritures --
    def illisible(self, motif: str):
        self.illisibles[motif] = self.illisibles.get(motif, 0) + 1

    def rejeter(self, motif: str):
        self.rejets[motif] = self.rejets.get(motif, 0) + 1

    # --------------------------------------------------------- totaux --
    @property
    def total_illisibles(self) -> int:
        return sum(self.illisibles.values())

    @property
    def total_rejets(self) -> int:
        return sum(self.rejets.values())

    @property
    def total_fusionnes(self) -> int:
        """Un doublon POSSIBLE n'est pas fusionné : il ne se soustrait pas."""
        return self.doublons_certains + self.doublons_probables

    @property
    def apres_lots(self) -> int:
        return self.normalisees + self.lots_ajoutes

    @property
    def sorties(self) -> int:
        return self.capter + self.developper

    # ---------------------------------------------------- réconciliation --
    def ecart(self) -> int:
        """Ce qui entre doit sortir, ou avoir un motif. L'écart doit être nul."""
        attendu = self.apres_lots - self.total_fusionnes - self.total_rejets
        return attendu - self.sorties

    def verifier(self):
        if self.brutes != self.normalisees + self.total_illisibles:
            raise ReconciliationImpossible(
                f"{self.brutes} lignes brutes ≠ {self.normalisees} normalisées "
                f"+ {self.total_illisibles} illisibles")
        e = self.ecart()
        if e != 0:
            raise ReconciliationImpossible(
                f"{abs(e)} opportunité(s) {'perdue(s)' if e > 0 else 'en trop'} "
                f"sans motif : {self.apres_lots} après lots "
                f"- {self.total_fusionnes} fusionnées - {self.total_rejets} rejetées "
                f"≠ {self.sorties} en sortie")

    # -------------------------------------------------------- rapport --
    def rapport(self) -> str:
        L = ["LIVRE DE COMPTES", "=" * 58, ""]
        L.append(f"  brutes                    {self.brutes:>6}")
        if self.illisibles:
            for motif, n in sorted(self.illisibles.items(), key=lambda x: -x[1]):
                L.append(f"    dont illisibles         -{n:<5} {motif[:34]}")
        L.append(f"  normalisées               {self.normalisees:>6}")
        L.append(f"  + lots éclatés            {self.lots_ajoutes:>+6}")
        L.append(f"  = après éclatement        {self.apres_lots:>6}")
        L.append(f"  - doublons certains       {self.doublons_certains:>6}")
        L.append(f"  - doublons probables      {self.doublons_probables:>6}")
        L.append(f"  - rejets                  {self.total_rejets:>6}")
        for motif, n in sorted(self.rejets.items(), key=lambda x: -x[1])[:8]:
            L.append(f"      {n:>4}  {motif[:44]}")
        L.append(f"  = CAPTER                  {self.capter:>6}")
        L.append(f"    DÉVELOPPER              {self.developper:>6}")
        L.append("")
        if self.doublons_possibles:
            L.append(f"  {self.doublons_possibles} doublon(s) POSSIBLE(S) reliés mais "
                     "NON fusionnés — à vérifier")
        e = self.ecart()
        L.append(f"  réconciliation            {'✔ exacte' if e == 0 else f'✗ écart de {e}'}")
        return "\n".join(L)
