"""ELIGIBLE · A_VERIFIER · NON_ELIGIBLE

Trois garde-fous, parce qu'un blocage à tort supprime un contrat :

  1. Seule une exigence STRUCTURÉE et obligatoire peut bloquer. Une exigence
     lue en texte libre ne produit qu'un A_VERIFIER.
  2. « A_VERIFIER » dans le profil ne vaut jamais NON_ELIGIBLE.
     Ne pas savoir n'est pas ne pas pouvoir.
  3. La capacité ACTUELLE n'est pas la capacité MAXIMALE. Une exigence de
     10 véhicules face à 6 possédés mais 20 mobilisables est une réserve, pas
     un blocage.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

INCONNU = {"A_VERIFIER", "À CONFIRMER", "A CONFIRMER", None, ""}


class Statut(Enum):
    ELIGIBLE = "ELIGIBLE"
    A_VERIFIER = "A_VERIFIER"
    NON_ELIGIBLE = "NON_ELIGIBLE"


@dataclass
class Exigence:
    code: str
    valeur: object = True
    texte: str = ""
    structuree: bool = True
    obligatoire: bool = True


@dataclass
class Resultat:
    statut: Statut = Statut.ELIGIBLE
    atouts: list[str] = field(default_factory=list)
    a_verifier: list[str] = field(default_factory=list)
    bloquants: list[str] = field(default_factory=list)
    inconnues: int = 0


def _flotte_totale(profil) -> int:
    return sum(v.get("nombre", 0) for v in profil.get("flotte", {}).get("actuelle", []))


def _capacites(profil: dict) -> dict:
    q = profil.get("qualifications", {})
    d = profil.get("depot", {})
    f = profil.get("flotte", {})
    return {
        "afsca": q.get("agrement_afsca"),
        "gdp": q.get("gdp_pharmaceutique"),
        "licence": q.get("licences_transport_spf"),
        "rc_vehicules_confies": q.get("rc_vehicules_confies"),
        "froid": d.get("froid_positif"),
        "surface_min_m2": d.get("surface_m2"),
        "vehicules_actuels": _flotte_totale(profil),
        "vehicules_max": f.get("vehicules_mobilisables_max", _flotte_totale(profil)),
        "extensible": bool(f.get("extensible_par_location")),
        "anciennete_min_annees": profil.get("entreprise", {}).get("anciennete_annees"),
    }


def evaluer(exigences: list[Exigence], profil: dict, ontologie_exigences: dict) -> Resultat:
    cap = _capacites(profil)
    r = Resultat()

    for e in exigences:
        spec = ontologie_exigences.get(e.code, {})
        libelle = spec.get("libelle", e.code.replace("_", " "))
        jamais_supposee = bool(spec.get("jamais_supposee"))

        # --- exigences numériques de capacité, avec extensibilité ---
        if e.code == "vehicules_min":
            besoin = int(e.valeur or 0)
            if cap["vehicules_actuels"] >= besoin:
                r.atouts.append(f"{besoin} véhicules exigés — {cap['vehicules_actuels']} en flotte")
            elif cap["extensible"] and besoin <= cap["vehicules_max"]:
                r.a_verifier.append(
                    f"{besoin} véhicules exigés, {cap['vehicules_actuels']} en propre — "
                    f"complément par location (jusqu'à {cap['vehicules_max']}) ; "
                    "vérifier si une flotte en propre est imposée")
            elif e.structuree and e.obligatoire:
                r.bloquants.append(
                    f"{besoin} véhicules exigés — au-delà du maximum mobilisable "
                    f"({cap['vehicules_max']})")
            else:
                r.a_verifier.append(f"{besoin} véhicules exigés — à confirmer")
            continue

        if e.code == "surface_min_m2":
            besoin = float(e.valeur or 0)
            surface = cap["surface_min_m2"]
            if surface in INCONNU:
                r.a_verifier.append(f"{libelle} de {besoin:g} m² — surface du dépôt non renseignée")
                r.inconnues += 1
            elif surface >= besoin:
                r.atouts.append(f"{libelle} de {besoin:g} m² exigée — dépôt de {surface:g} m² à Bruxelles")
            elif e.structuree and e.obligatoire:
                r.bloquants.append(f"{libelle} de {besoin:g} m² exigée — dépôt de {surface:g} m²")
            else:
                r.a_verifier.append(f"{libelle} de {besoin:g} m² — exigence lue en texte libre")
            continue

        if e.code == "anciennete_min_annees":
            besoin = float(e.valeur or 0)
            ans = cap["anciennete_min_annees"]
            if ans in INCONNU:
                r.a_verifier.append(f"{besoin:g} ans d'ancienneté exigés — à confirmer")
                r.inconnues += 1
            elif ans >= besoin:
                r.atouts.append(f"{besoin:g} ans d'ancienneté exigés — {ans} an(s) d'existence")
            else:
                # Souvent contournable par références ou garantie : jamais bloquant seul.
                r.a_verifier.append(
                    f"{besoin:g} ans d'ancienneté ou de comptes exigés — l'entreprise a {ans} an(s) ; "
                    "vérifier si des références équivalentes sont acceptées")
            continue

        # --- exigences binaires (certifications, agréments, assurances) ---
        detenue = cap.get(e.code)
        if detenue is True or (isinstance(detenue, (int, float)) and detenue and not jamais_supposee):
            r.atouts.append(f"{libelle} exigé — détenu")
        elif detenue in INCONNU or jamais_supposee:
            # Jamais supposée acquise : c'est la règle du pharmaceutique.
            r.a_verifier.append(f"{libelle} exigé — non confirmé au profil, à vérifier")
            r.inconnues += 1
        elif e.structuree and e.obligatoire:
            r.bloquants.append(f"{libelle} exigé et non détenu")
        else:
            r.a_verifier.append(f"{libelle} exigé — exigence lue en texte libre, à confirmer")

    if r.bloquants:
        r.statut = Statut.NON_ELIGIBLE
    elif r.a_verifier:
        r.statut = Statut.A_VERIFIER
    return r
