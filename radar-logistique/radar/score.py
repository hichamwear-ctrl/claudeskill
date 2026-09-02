"""Le score CLASSE, il n'écarte jamais.

Une opportunité à 30/100 reste livrée si elle est postulable : elle arrive en
bas de liste. Chaque point est tracé — on doit toujours pouvoir répondre à
« pourquoi ce score ? ».

Toutes les pondérations viennent de config/ponderations.yaml.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .geographie import Zone
from .modele import Nature


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
        self.b = config.get("bonus", {})
        self.cfg = config

    def _palier(self, paliers, valeur, defaut):
        if valeur is None:
            return defaut
        for p in paliers:
            if valeur >= p["min"]:
                return p["points"]
        return defaut

    def calculer(self, *, correspondance, zone, eligibilite, opp, jours_restants) -> Score:
        lignes: list[Ligne] = []
        maxi = self.c

        # --- activité : le critère le plus lourd ---
        if correspondance.familles:
            part = min(len(correspondance.familles) / 2, 1.0)
            pts = maxi["activite"] * part
            preuves = [t for v in correspondance.preuves.values() for t in v][:3]
            raison = f"{len(correspondance.familles)} famille(s) reconnue(s)"
            if preuves:
                raison += f" via « {' / '.join(preuves)} »"
            elif correspondance.par_cpv:
                raison += f" via CPV {', '.join(correspondance.par_cpv[:2])}"
            lignes.append(Ligne("activité", round(pts, 1), raison))
        else:
            lignes.append(Ligne("activité", 0, "aucune famille d'activité reconnue"))

        # --- zone : le corridor vaut le maximum ---
        bareme_zone = {Zone.CORRIDOR: 1.0, Zone.NATIONAL: 0.7, Zone.A_VERIFIER: 0.4,
                       Zone.HORS_ZONE: 0.0}
        pts = maxi["zone"] * bareme_zone[zone.zone]
        lignes.append(Ligne("zone", round(pts, 1), zone.raisons[0] if zone.raisons else zone.zone.value))
        if zone.corridor_eprouve:
            lignes.append(Ligne("corridor éprouvé", self.b.get("corridor_eprouve", 0),
                                "trajet déjà exécuté — référence directe"))

        # --- capacité ---
        if eligibilite.bloquants:
            lignes.append(Ligne("capacité", 0, "exigence hors capacité"))
        elif not eligibilite.a_verifier:
            lignes.append(Ligne("capacité", maxi["capacite"], "toutes les exigences couvertes"))
        else:
            lignes.append(Ligne("capacité", maxi["capacite"] * 0.6,
                                f"{len(eligibilite.a_verifier)} point(s) à confirmer"))

        # --- expérience similaire ---
        if zone.corridor_eprouve or any(f in ("volumineux", "dernier_kilometre",
                                              "transport_international", "alimentaire")
                                        for f in correspondance.familles):
            lignes.append(Ligne("expérience similaire", maxi["experience_similaire"],
                                "prestation proche de références déjà exécutées"))
        else:
            lignes.append(Ligne("expérience similaire", 0, "pas de référence directe"))

        # --- montant ---
        if opp.montant:
            pts = self._palier(self.cfg["montant_paliers"], opp.montant, 0)
            lignes.append(Ligne("montant", pts, f"{opp.montant:,.0f} {opp.devise}".replace(",", " ")))
        else:
            lignes.append(Ligne("montant", self.cfg["montant_non_publie_points"],
                                "montant non publié — score neutre, pas de pénalité"))

        # --- échéance ---
        if jours_restants is None:
            lignes.append(Ligne("échéance", self.cfg["echeance_inconnue_points"],
                                "échéance non confirmée"))
        else:
            pts = self._palier(self.cfg["echeance_paliers"], jours_restants, 0)
            lignes.append(Ligne("échéance", pts, f"{jours_restants} jour(s) pour déposer"))

        # --- durée et récurrence ---
        if opp.duree_mois and opp.duree_mois >= self.b.get("duree_longue_mois", 36):
            lignes.append(Ligne("durée", self.b.get("duree_longue_points", 0),
                                f"contrat de {opp.duree_mois} mois"))
        if opp.recurrent:
            lignes.append(Ligne("récurrence", self.b.get("contrat_recurrent", 0),
                                "prestation récurrente, pas ponctuelle"))

        # --- pénalité d'incertitude ---
        if eligibilite.inconnues:
            lignes.append(Ligne("exigences inconnues", maxi["exigences_inconnues"],
                                f"{eligibilite.inconnues} exigence(s) non confirmée(s)"))

        total = sum(l.points for l in lignes)
        if opp.nature is Nature.SIGNAL_COMMERCIAL:
            facteur = self.cfg.get("facteur_signal_commercial", 1.0)
            total *= facteur
            lignes.append(Ligne("signal commercial", 0,
                                f"score pondéré ×{facteur} — moins certain qu'un appel d'offres"))
        return Score(max(0, min(100, round(total))), lignes)
