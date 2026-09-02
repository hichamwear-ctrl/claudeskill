"""Qui fournit le produit, qui réalise la prestation ?

« Fourniture et livraison de poissons » contient « livraison » et n'est PAS un
marché de transport : l'acheteur veut du poisson. L'entreprise vend une
prestation, jamais un produit — elle ne doit donc apparaître que lorsque la
prestation logistique est l'objet même du marché ou d'un de ses lots.

C'est le filtre qui sépare un radar utile d'un moteur de recherche de mots-clés.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .activite import normaliser


class Role(Enum):
    PRESTATAIRE = "PRESTATAIRE"      # la prestation logistique EST l'objet
    FOURNISSEUR = "FOURNISSEUR"      # l'acheteur veut un bien — hors métier
    A_VERIFIER = "A_VERIFIER"        # signaux absents ou contradictoires

    @property
    def exploitable(self) -> bool:
        """Un FOURNISSEUR est rejeté. Un A_VERIFIER descend au niveau du lot."""
        return self is not Role.FOURNISSEUR


@dataclass
class Analyse:
    role: Role
    preuves: list[str] = field(default_factory=list)
    contre_preuves: list[str] = field(default_factory=list)
    cpv_decisif: str | None = None


class DetecteurDeRole:
    def __init__(self, config: dict):
        self.cpv_prestation = tuple(str(c) for c in config["cpv"]["prestation"])
        self.cpv_fourniture = tuple(str(c) for c in config["cpv"]["fourniture"])
        self.cpv_travaux = tuple(str(c) for c in config["cpv"].get("travaux", []))
        self.mots_fourniture = self._mots(config["lexique"]["fourniture"])
        self.mots_prestation = self._mots(config["lexique"]["prestation"])
        self.regles = config.get("regles", {})

    @staticmethod
    def _mots(par_langue: dict) -> list[str]:
        sortie = []
        for langue in ("fr", "nl", "en"):
            sortie += [normaliser(m).strip() for m in par_langue.get(langue, [])]
        return [m for m in sortie if m]

    def _classer_cpv(self, codes) -> tuple[str | None, str | None]:
        """Renvoie (famille, code décisif). Le CPV est le signal le plus fiable."""
        for code in codes or []:
            c = str(code).strip()
            if c.startswith(self.cpv_prestation):
                return "prestation", c
        for code in codes or []:
            c = str(code).strip()
            if c.startswith(self.cpv_travaux):
                return "travaux", c
            if c.startswith(self.cpv_fourniture):
                return "fourniture", c
        return None, None

    def analyser(self, texte: str, cpv=None) -> Analyse:
        plat = normaliser(texte)
        famille, code = self._classer_cpv(cpv)

        trouves_f = [m for m in self.mots_fourniture if f" {m} " in plat or plat.startswith(f" {m}")]
        trouves_p = [m for m in self.mots_prestation if f" {m} " in plat]

        # 1. Le CPV tranche quand il est présent.
        if famille == "prestation":
            return Analyse(Role.PRESTATAIRE,
                           preuves=[f"CPV {code} : services de transport ou de logistique"]
                                   + [f"« {m} »" for m in trouves_p[:2]],
                           contre_preuves=[f"« {m} »" for m in trouves_f[:2]],
                           cpv_decisif=code)
        if famille == "travaux":
            return Analyse(Role.FOURNISSEUR,
                           contre_preuves=[f"CPV {code} : marché de travaux"], cpv_decisif=code)
        if famille == "fourniture" and self.regles.get("cpv_fourniture_domine", True):
            # Le piège classique : « fourniture ET livraison ». Le mot livraison
            # ne rachète pas un CPV de fourniture au niveau du marché entier —
            # mais un LOT pourra isoler la prestation.
            return Analyse(Role.FOURNISSEUR,
                           preuves=[f"« {m} »" for m in trouves_p[:2]],
                           contre_preuves=[f"CPV {code} : l'acheteur acquiert un bien"]
                                          + [f"« {m} »" for m in trouves_f[:2]],
                           cpv_decisif=code)

        # 2. Sans CPV, on arbitre sur le lexique.
        if trouves_p and not trouves_f:
            return Analyse(Role.PRESTATAIRE, preuves=[f"« {m} »" for m in trouves_p[:3]])
        if trouves_f and not trouves_p:
            return Analyse(Role.FOURNISSEUR,
                           contre_preuves=[f"« {m} »" for m in trouves_f[:3]])
        if trouves_f and trouves_p:
            return Analyse(Role.A_VERIFIER,
                           preuves=[f"« {m} »" for m in trouves_p[:2]],
                           contre_preuves=[f"« {m} »" for m in trouves_f[:2]])
        return Analyse(Role.A_VERIFIER,
                       contre_preuves=["aucun signal permettant de dire qui fournit quoi"])
