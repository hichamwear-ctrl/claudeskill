"""Croise les exigences publiées avec le profil de l'exploitant.

Produit la réponse à « pourquoi je corresponds à ce marché », et le cas échéant
ce qui manque pour y répondre.

Deux garde-fous, parce qu'un blocage à tort fait disparaître un contrat :

  1. Seule une exigence STRUCTURÉE (lue dans un champ normé) peut bloquer. Une
     exigence déduite d'un texte libre ne produit qu'une réserve.
  2. Une capacité NON VÉRIFIÉE du profil ne bloque jamais. « Je ne sais pas »
     n'est pas « je ne peux pas ».
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

INCONNU = {"À CONFIRMER", "A CONFIRMER", None, ""}


class Statut(Enum):
    ELIGIBLE = "éligible"
    SOUS_RESERVE = "éligible sous réserve"
    BLOQUE = "non éligible"

    @property
    def peut_deposer(self) -> bool:
        return self is not Statut.BLOQUE


@dataclass
class Exigence:
    code: str
    valeur: object = True
    texte: str = ""
    structuree: bool = True     # False = déduite d'un texte libre -> ne bloque pas


@dataclass
class Resultat:
    statut: Statut
    atouts: list[str] = field(default_factory=list)     # « pourquoi ça correspond »
    reserves: list[str] = field(default_factory=list)
    blocages: list[str] = field(default_factory=list)

    @property
    def peut_deposer(self) -> bool:
        return self.statut.peut_deposer


def _connu(v):
    return v not in INCONNU


def _profil_capacites(profil: dict) -> dict:
    """Aplatit le profil YAML en capacités comparables aux exigences."""
    cap = profil.get("capacite", {})
    qual = profil.get("qualifications", {})
    dep, veh, ch = cap.get("depot", {}), cap.get("vehicules", {}), cap.get("chauffeurs", {})
    return {
        "afsca":            qual.get("agrement_afsca"),
        "licences":         qual.get("licences_transport_spf"),
        "surface_m2":       dep.get("surface_m2"),
        "froid":            dep.get("froid_positif"),
        "tri_colis":        dep.get("tri_colis"),
        "vehicules":        veh.get("possedes"),
        "vehicules_locables": veh.get("location_sur_contrat"),
        "chauffeurs_extensibles": ch.get("extensible"),
        "segments":         [r.get("segment", "") for r in profil.get("references", [])
                             if r.get("active") is True],
    }


def evaluer(exigences: list[Exigence], profil: dict) -> Resultat:
    cap = _profil_capacites(profil)
    atouts: list[str] = []
    reserves: list[str] = []
    blocages: list[str] = []

    def tranche(code, ok, atout, manque, detail=""):
        """Répartit une exigence entre atout, réserve et blocage."""
        exi = next(e for e in exigences if e.code == code)
        if ok is True:
            atouts.append(atout)
        elif ok is None:
            reserves.append(f"{manque} — capacité non vérifiée au profil")
        elif exi.structuree:
            blocages.append(f"{manque}{detail}")
        else:
            reserves.append(f"{manque} — exigence lue en texte libre, à confirmer{detail}")

    for e in exigences:
        if e.code == "afsca_requis" and e.valeur:
            v = cap["afsca"]
            tranche("afsca_requis", True if v is True else (None if not _connu(v) else False),
                    "agrément AFSCA exigé — tu l'as, la plupart des transporteurs non",
                    "agrément AFSCA exigé et non détenu")

        elif e.code == "licence_transport_requise" and e.valeur:
            n = cap["licences"]
            ok = True if (_connu(n) and n) else (None if not _connu(n) else False)
            tranche("licence_transport_requise", ok,
                    f"licence de transport exigée — tu en as {n}, ça élimine les non-licenciés",
                    "licence de transport exigée et non détenue")

        elif e.code == "surface_min_m2":
            s, besoin = cap["surface_m2"], e.valeur
            ok = None if not _connu(s) else (s >= besoin)
            tranche("surface_min_m2", ok,
                    f"site de {besoin} m² exigé — ton dépôt fait {s} m² à Bruxelles",
                    f"surface exigée {besoin} m²",
                    f" — ton dépôt fait {s} m²" if _connu(s) else "")

        elif e.code == "froid_requis" and e.valeur:
            v = cap["froid"]
            tranche("froid_requis", True if v is True else (None if not _connu(v) else False),
                    "température dirigée exigée — capacité froid disponible",
                    "température dirigée exigée")

        elif e.code == "vehicules_min":
            n, besoin = cap["vehicules"], e.valeur
            if _connu(n) and n >= besoin:
                atouts.append(f"{besoin} véhicules exigés — tu en as {n}")
            elif cap["vehicules_locables"]:
                reserves.append(
                    f"{besoin} véhicules exigés, tu en as {n} — complément par location "
                    "sur contrat signé ; vérifie si une flotte en propre est imposée")
            else:
                tranche("vehicules_min", False, "", f"{besoin} véhicules exigés, tu en as {n}")

        elif e.code == "reference_segment":
            besoin = str(e.valeur).lower()
            trouve = [s for s in cap["segments"] if any(m in s.lower() for m in besoin.split())]
            if trouve:
                atouts.append(f"référence « {besoin} » exigée — tu as : {trouve[0]}")
            elif e.structuree:
                blocages.append(f"référence « {besoin} » exigée et absente du profil")
            else:
                reserves.append(f"référence « {besoin} » attendue — à vérifier dans le cahier des charges")

        elif e.code == "tri_colis_requis" and e.valeur:
            if cap["tri_colis"] is True:
                atouts.append("capacité de tri exigée — ton dépôt trie déjà")
            else:
                reserves.append("capacité de tri exigée — à confirmer")

        else:
            # Exigence non modélisée : jamais bloquante, toujours signalée.
            if e.texte:
                reserves.append(f"exigence non évaluée automatiquement : {e.texte}")

    if blocages:
        return Resultat(Statut.BLOQUE, atouts, reserves, blocages)
    if reserves:
        return Resultat(Statut.SOUS_RESERVE, atouts, reserves, blocages)
    return Resultat(Statut.ELIGIBLE, atouts, reserves, blocages)
