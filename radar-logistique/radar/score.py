"""Score adapté à une PME de transport récente.

Il ne mesure pas la taille du marché, il mesure la probabilité d'aller le
chercher et d'en vivre. Un contrat de 8 000 €/mois sur deux ans bat un marché
de 5 M€ qui exige une structure absente.

Il CLASSE, il n'élimine pas : les exigences bloquantes vivent dans capacite.py,
séparément. Chaque point est justifié.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .classification import Type
from .geographie import Zone


@dataclass
class Ligne:
    critere: str
    points: float
    raison: str


@dataclass
class Score:
    total: int
    lignes: list[Ligne] = field(default_factory=list)

    def detail(self) -> list[str]:
        return [f"{l.critere} : {l.points:+g} — {l.raison}" for l in self.lignes]


class Bareme:
    def __init__(self, config: dict):
        self.c = config["criteres"]
        self.pen = config["penalites"]
        self.taille = config["taille"]
        self.rec = config["recurrence"]
        self.conc = config["concurrence"]
        self.facteurs = config["facteurs"]

    # ------------------------------------------------------------- taille --
    def _taille(self, montant, duree_mois) -> tuple[float, str]:
        t = self.taille
        if not montant:
            return t["points_non_publie"], "montant non publié — neutre, jamais pénalisant"
        if montant > t["hors_gabarit_au_dela"]:
            return t["points_hors_gabarit"], (
                f"{montant:,.0f} € — hors gabarit en titulaire direct".replace(",", " "))
        mois = duree_mois or 12
        mensuel = montant / max(mois, 1)
        if t["mensuel_ideal_min"] <= mensuel <= t["mensuel_ideal_max"]:
            return t["points_dans_la_cible"], (
                f"{mensuel:,.0f} €/mois — dans la cible économique".replace(",", " "))
        if montant <= t["total_confortable_max"]:
            return t["points_proche"], (
                f"{mensuel:,.0f} €/mois — proche de la cible".replace(",", " "))
        return t["points_hors_cible"], (
            f"{montant:,.0f} € — au-dessus du confortable".replace(",", " "))

    # --------------------------------------------------------- récurrence --
    def _recurrence(self, cadence) -> tuple[float, str]:
        cle = (cadence or "inconnue").lower()
        pts = self.rec.get(cle, self.rec["inconnue"])
        libelle = {"quotidienne": "tournée quotidienne", "hebdomadaire": "flux hebdomadaire",
                   "mensuelle": "besoin mensuel", "pluriannuelle": "contrat pluriannuel",
                   "ponctuelle": "prestation ponctuelle"}.get(cle, "cadence non publiée")
        return pts, libelle

    # -------------------------------------------------------- concurrence --
    def _concurrence(self, montant, exigences) -> tuple[float, str]:
        indices = []
        if montant and montant >= self.conc["seuil_montant_gros_acteurs"]:
            indices.append(f"montant de {montant:,.0f} €".replace(",", " "))
        if exigences.get("chiffre_affaires_min", 0) >= self.conc["seuil_ca_exige"]:
            indices.append("chiffre d'affaires minimum élevé")
        if exigences.get("anciennete_min_annees", 0) >= self.conc["seuil_anciennete_exigee"]:
            indices.append("ancienneté élevée exigée")
        if not indices:
            return 0, ""
        return self.pen["concurrence_grands_acteurs"], (
            "marché probablement disputé par de grands acteurs : " + ", ".join(indices))

    # ------------------------------------------------------------ calcul --
    def calculer(self, *, correspondance, zone, bilan, opp, type_opp: Type,
                 cadence=None, jours_restants=None) -> Score:
        L: list[Ligne] = []
        c = self.c

        # 1. Sais-je faire ?
        if correspondance.familles:
            part = min(len(correspondance.familles) / 2, 1.0)
            preuves = [t for v in correspondance.preuves.values() for t in v][:2]
            L.append(Ligne("adéquation opérationnelle", round(c["adequation_operationnelle"] * part, 1),
                           f"{len(correspondance.familles)} famille(s) reconnue(s)"
                           + (f" via « {' / '.join(preuves)} »" if preuves else "")))
        else:
            L.append(Ligne("adéquation opérationnelle", 0, "aucune famille reconnue"))

        # 2. Une PME récente peut-elle concourir ?
        if bilan.bloquants:
            acces, raison = 0, "exigence hors capacité"
        elif not bilan.a_verifier and not bilan.mobilisations:
            acces, raison = c["accessibilite_pme"], "toutes les exigences couvertes en l'état"
        elif bilan.mobilisations and not bilan.a_verifier:
            acces, raison = c["accessibilite_pme"] * 0.8, "accessible après mobilisation de moyens"
        else:
            acces = c["accessibilite_pme"] * 0.55
            raison = f"{len(bilan.a_verifier)} exigence(s) à confirmer"
        L.append(Ligne("accessibilité PME", round(acces, 1), raison))

        # 3. Géographie
        bareme = {Zone.CORRIDOR: 1.0, Zone.NATIONAL: 0.75, Zone.A_VERIFIER: 0.4,
                  Zone.HORS_ZONE: 0.0}
        L.append(Ligne("géographie", round(c["geographie"] * bareme[zone.zone], 1),
                       zone.raisons[0] if zone.raisons else zone.zone.value))
        if zone.corridor_eprouve:
            L.append(Ligne("corridor éprouvé", 5, "trajet déjà exécuté — référence directe"))

        # 4. Taille adaptée
        pts, raison = self._taille(opp.montant, opp.duree_mois)
        L.append(Ligne("taille adaptée", pts, raison))

        # 5. Récurrence
        pts, raison = self._recurrence(cadence)
        L.append(Ligne("récurrence", pts, raison))

        # 6. Rapidité de démarrage
        if bilan.mobilisations:
            L.append(Ligne("rapidité de démarrage", round(c["rapidite_demarrage"] * 0.4, 1),
                           "démarrage conditionné à une location de matériel"))
        else:
            L.append(Ligne("rapidité de démarrage", c["rapidite_demarrage"],
                           "exécutable avec les moyens en place"))

        # 7. Rentabilité potentielle — neutre si le montant n'est pas publié.
        if opp.montant and opp.duree_mois:
            L.append(Ligne("rentabilité potentielle", c["rentabilite_potentielle"],
                           "montant et durée publiés — chiffrage possible"))
        else:
            L.append(Ligne("rentabilité potentielle", round(c["rentabilite_potentielle"] * 0.5, 1),
                           "montant ou durée non publiés — chiffrage à faire"))

        # 8. Pénalités
        if bilan.mobilisations:
            L.append(Ligne("complexité", self.pen["complexite_investissement"],
                           f"{len(bilan.mobilisations)} moyen(s) à mobiliser avant de démarrer"))
        if bilan.a_verifier:
            L.append(Ligne("exigences non confirmées", self.pen["exigences_non_confirmees"],
                           f"{len(bilan.a_verifier)} point(s) à vérifier"))
        pts, raison = self._concurrence(opp.montant, opp.exigences or {})
        if pts:
            L.append(Ligne("concurrence", pts, raison))

        total = sum(l.points for l in L)
        facteur = self.facteurs.get(type_opp.value, 1.0)
        if facteur != 1.0:
            total *= facteur
            L.append(Ligne("type d'opportunité", 0,
                           f"{type_opp.value} — score pondéré ×{facteur}"))
        return Score(max(0, min(100, round(total))), L)
