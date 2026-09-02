"""Les trois niveaux de capacité.

  ACTUELLE      ce qui est faisable tout de suite avec les ressources propres
  MOBILISABLE   ce qui est atteignable rapidement — location, renfort, partenaire
  NON DISPONIBLE ce qui exige une licence, une qualification ou une infrastructure
                 que l'entreprise n'a pas et ne peut pas raisonnablement obtenir

Règle : une capacité n'est JAMAIS présumée acquise parce qu'elle est
techniquement possible. Et une qualification ne se loue pas — la mobilisation
couvre du matériel et des bras, pas un agrément.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

INCONNU = {"A_VERIFIER", "À CONFIRMER", "A CONFIRMER", None, ""}


class Niveau(Enum):
    ACTUELLE = "ACTUELLE"
    MOBILISABLE = "MOBILISABLE"
    NON_DISPONIBLE = "NON_DISPONIBLE"
    A_VERIFIER = "A_VERIFIER"

    @property
    def bloquant(self) -> bool:
        return self is Niveau.NON_DISPONIBLE


@dataclass
class Reponse:
    niveau: Niveau
    message: str
    cout: str = ""          # ce qu'il faut engager pour y arriver


@dataclass
class Bilan:
    atouts: list[str] = field(default_factory=list)
    mobilisations: list[str] = field(default_factory=list)
    a_verifier: list[str] = field(default_factory=list)
    bloquants: list[str] = field(default_factory=list)
    investissement_requis: bool = False

    def ajouter(self, r: Reponse):
        if r.niveau is Niveau.ACTUELLE:
            self.atouts.append(r.message)
        elif r.niveau is Niveau.MOBILISABLE:
            self.mobilisations.append(r.message)
            self.investissement_requis = True
        elif r.niveau is Niveau.A_VERIFIER:
            self.a_verifier.append(r.message)
        else:
            self.bloquants.append(r.message)


class Capacites:
    """Confronte une exigence au profil, en trois niveaux."""

    def __init__(self, profil: dict, libelles: dict | None = None):
        self.p = profil
        self.actuelle = profil.get("capacite_actuelle", {})
        self.mobilisable = profil.get("capacite_mobilisable", {})
        self.qualifs = profil.get("qualifications", {})
        self.libelles = libelles or {}
        self.mobilisation_ne_couvre_pas = set(
            self.mobilisable.get("ne_couvre_pas", []))

    # ------------------------------------------------------------ véhicules --
    def vehicules(self, besoin: int) -> Reponse:
        actuel = self.actuelle.get("vehicules_total", 0)
        maxi = self.mobilisable.get("vehicules_total_max", actuel)
        if besoin <= actuel:
            return Reponse(Niveau.ACTUELLE, f"{besoin} véhicules exigés — {actuel} en flotte")
        if besoin <= maxi:
            manque = besoin - actuel
            return Reponse(
                Niveau.MOBILISABLE,
                f"{besoin} véhicules exigés — {actuel} en propre, {manque} à louer "
                f"(mobilisable jusqu'à {maxi})",
                cout=f"location de {manque} véhicule(s), "
                     f"{self.mobilisable.get('delai_mobilisation_jours', '?')} j")
        return Reponse(Niveau.NON_DISPONIBLE,
                       f"{besoin} véhicules exigés — au-delà du maximum mobilisable ({maxi})")

    # -------------------------------------------------------------- surface --
    def surface(self, besoin: float) -> Reponse:
        depot = self.actuelle.get("depot", {})
        surface = depot.get("surface_m2")
        if surface in INCONNU:
            return Reponse(Niveau.A_VERIFIER, f"surface de {besoin:g} m² exigée — dépôt non renseigné")
        if surface >= besoin:
            return Reponse(Niveau.ACTUELLE, f"{besoin:g} m² exigés — dépôt de {surface:g} m² à Bruxelles")
        # Un entrepôt ne se loue pas dans le délai d'un marché : c'est structurel.
        return Reponse(Niveau.NON_DISPONIBLE,
                       f"{besoin:g} m² exigés — dépôt de {surface:g} m², extension hors délai")

    # -------------------------------------------------- qualifications --
    def qualification(self, code: str) -> Reponse:
        libelle = self.libelles.get(code, {}).get("libelle", code.replace("_", " "))
        valeur = self.qualifs.get(code)
        if valeur is True:
            return Reponse(Niveau.ACTUELLE, f"{libelle} exigé — détenu")
        if valeur is False:
            # Déclaré explicitement absent : une qualification ne se loue pas.
            return Reponse(Niveau.NON_DISPONIBLE,
                           f"{libelle} exigé — explicitement non détenu et non mobilisable")
        # Inconnu : ne jamais trancher dans un sens ni dans l'autre.
        return Reponse(Niveau.A_VERIFIER, f"{libelle} exigé — non confirmé au profil")

    # -------------------------------------------------------- ancienneté --
    def anciennete(self, besoin: float) -> Reponse:
        ans = self.p.get("entreprise", {}).get("anciennete_annees")
        if ans in INCONNU:
            return Reponse(Niveau.A_VERIFIER, f"{besoin:g} ans exigés — ancienneté non renseignée")
        if ans >= besoin:
            return Reponse(Niveau.ACTUELLE, f"{besoin:g} ans exigés — {ans} an(s) d'existence")
        # Souvent contournable par références équivalentes ou garantie : jamais
        # bloquant à lui seul pour une entreprise récente.
        return Reponse(Niveau.A_VERIFIER,
                       f"{besoin:g} ans d'existence ou de comptes exigés — l'entreprise a {ans} an(s) ; "
                       "vérifier si des références équivalentes sont acceptées")

    # --------------------------------------------------- chiffre d'affaires --
    def chiffre_affaires(self, besoin: float) -> Reponse:
        ca = self.p.get("entreprise", {}).get("chiffre_affaires_annuel")
        if ca in INCONNU:
            return Reponse(Niveau.A_VERIFIER,
                           f"chiffre d'affaires minimum de {besoin:,.0f} € exigé — "
                           "le tien n'est pas renseigné au profil".replace(",", " "))
        if ca >= besoin:
            return Reponse(Niveau.ACTUELLE, f"chiffre d'affaires minimum de {besoin:,.0f} € atteint".replace(",", " "))
        return Reponse(Niveau.NON_DISPONIBLE,
                       f"chiffre d'affaires minimum de {besoin:,.0f} € exigé — non atteint".replace(",", " "))

    # ----------------------------------------------------------- références --
    def references(self, besoin: int) -> Reponse:
        n = self.p.get("entreprise", {}).get("contrats_similaires_realises")
        if n in INCONNU:
            return Reponse(Niveau.A_VERIFIER, f"{besoin} références similaires exigées — non renseignées")
        if n >= besoin:
            return Reponse(Niveau.ACTUELLE, f"{besoin} références exigées — {n} disponibles")
        return Reponse(Niveau.A_VERIFIER,
                       f"{besoin} références similaires exigées — {n} disponible(s) ; "
                       "vérifier si des prestations proches sont recevables")
