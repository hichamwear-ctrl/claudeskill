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
        """Le CPV est UNE preuve, pas une autorité.

        Il tranchait tout : un texte disant « prestations de transport et
        distribution quotidienne » ressortait FOURNISSEUR parce qu'un CPV
        indiquait des fournitures de bureau. Une nomenclature propre aux
        marchés publics écrasait donc la description du besoin — et un besoin
        privé, qui n'a jamais de CPV, ne pouvait par construction jamais
        bénéficier de cette autorité. C'était un privilège structurel.

        Même logique de résolution que pour l'état de procédure :
          · les deux preuves concordent  → conclusion, confiance haute ;
          · une seule preuve existe      → elle conclut ;
          · les deux se contredisent     → A_VERIFIER, les deux affichées.
        Aucun gagnant arbitraire.
        """
        plat = normaliser(texte)
        famille, code = self._classer_cpv(cpv)

        trouves_f = [m for m in self.mots_fourniture
                     if f" {m} " in plat or plat.startswith(f" {m}")]
        trouves_p = [m for m in self.mots_prestation if f" {m} " in plat]

        # Ce que dit le TEXTE, seul.
        if trouves_p and not trouves_f:
            texte_dit = "prestation"
        elif trouves_f and not trouves_p:
            texte_dit = "fourniture"
        elif trouves_f and trouves_p:
            texte_dit = "mixte"
        else:
            texte_dit = None

        # Ce que dit le CPV, seul. « travaux » se comporte comme « fourniture » :
        # l'acheteur n'achète pas une prestation de transport.
        cpv_dit = {"prestation": "prestation", "fourniture": "fourniture",
                   "travaux": "fourniture"}.get(famille)

        preuves_p = [f"« {m} »" for m in trouves_p[:2]]
        preuves_f = [f"« {m} »" for m in trouves_f[:2]]
        libelle_cpv = {
            "prestation": f"CPV {code} : services de transport ou de logistique",
            "fourniture": f"CPV {code} : l'acheteur acquiert un bien",
            "travaux": f"CPV {code} : marché de travaux",
        }.get(famille)

        # 1. Aucune des deux preuves : on ne sait pas, et on le dit.
        if cpv_dit is None and texte_dit is None:
            return Analyse(Role.A_VERIFIER,
                           contre_preuves=["aucun signal permettant de dire "
                                           "qui fournit quoi"])

        # 2. Une seule preuve disponible : elle conclut, sans privilège.
        if cpv_dit is None:
            if texte_dit == "prestation":
                return Analyse(Role.PRESTATAIRE, preuves=preuves_p)
            if texte_dit == "fourniture":
                return Analyse(Role.FOURNISSEUR, contre_preuves=preuves_f)
            return Analyse(Role.A_VERIFIER, preuves=preuves_p,
                           contre_preuves=preuves_f)
        if texte_dit is None:
            role = Role.PRESTATAIRE if cpv_dit == "prestation" else Role.FOURNISSEUR
            return Analyse(role, cpv_decisif=code,
                           preuves=[libelle_cpv] if role is Role.PRESTATAIRE else [],
                           contre_preuves=[] if role is Role.PRESTATAIRE
                           else [libelle_cpv])

        # 3. Les deux concordent : conclusion nette.
        if texte_dit == cpv_dit == "prestation":
            return Analyse(Role.PRESTATAIRE, preuves=[libelle_cpv] + preuves_p,
                           contre_preuves=preuves_f, cpv_decisif=code)
        if texte_dit == cpv_dit == "fourniture":
            return Analyse(Role.FOURNISSEUR, preuves=preuves_p,
                           contre_preuves=[libelle_cpv] + preuves_f, cpv_decisif=code)

        # 4. Un texte MIXTE — « fourniture ET livraison » — laisse le CPV
        #    départager : il n'écrase rien, il éclaire une ambiguïté réelle.
        if texte_dit == "mixte":
            role = Role.PRESTATAIRE if cpv_dit == "prestation" else Role.FOURNISSEUR
            return Analyse(role, preuves=([libelle_cpv] if role is Role.PRESTATAIRE
                                          else []) + preuves_p,
                           contre_preuves=([] if role is Role.PRESTATAIRE
                                           else [libelle_cpv]) + preuves_f,
                           cpv_decisif=code)

        # 5. CONTRADICTION FRANCHE entre la nomenclature et la description.
        #    Personne ne gagne : on conserve les deux et on demande à vérifier.
        #    A_VERIFIER n'est pas un rejet — l'opportunité reste dans le radar.
        return Analyse(Role.A_VERIFIER,
                       preuves=([libelle_cpv] if cpv_dit == "prestation" else [])
                               + preuves_p,
                       contre_preuves=([libelle_cpv] if cpv_dit == "fourniture" else [])
                                      + preuves_f
                               + [f"la nomenclature dit {cpv_dit}, le texte dit "
                                  f"{texte_dit} — contradiction à trancher"],
                       cpv_decisif=code)
