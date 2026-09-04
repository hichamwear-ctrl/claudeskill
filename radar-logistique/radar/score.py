"""Score adapté à une PME de transport récente.

Il CLASSE, il n'élimine jamais. Les exigences bloquantes vivent dans
capacite.py, séparément.

CHANGEMENT : le score raisonne désormais en
    CA × effort × investissement × risque × marge × adéquation × proximité
et non plus principalement sur le montant. Un contrat de 8 000 €/mois avec peu
de kilomètres passe devant 500 000 € gourmands en véhicules et en personnel.

La marge n'est calculée QUE si les coûts d'exploitation sont renseignés au
profil. Sinon elle vaut NON MESURÉE et reste neutre : l'absence de donnée ne
pénalise jamais une opportunité.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .classification import Type
from .geographie import Zone

NON_MESUREE = "NON MESURÉE"


@dataclass
class Ligne:
    critere: str
    points: float
    raison: str


@dataclass
class Score:
    total: int
    lignes: list[Ligne] = field(default_factory=list)
    marge_estimee: str = NON_MESUREE

    def detail(self) -> list[str]:
        return [f"{l.critere} : {l.points:+g} — {l.raison}" for l in self.lignes]


class Bareme:
    def __init__(self, config: dict, profil: dict | None = None):
        self.c = config["criteres"]
        self.sup = config.get("criteres_supplementaires", {})
        self.pen = config["penalites"]
        self.taille = config["taille"]
        self.rec = config["recurrence"]
        self.conc = config["concurrence"]
        self.effort = config.get("effort", {})
        self.cfg_marge = config.get("marge", {})
        # Le maximum réellement atteignable, calculé depuis la configuration —
        # jamais une constante écrite à la main qui se désynchroniserait au
        # premier réglage de poids.
        self.plafond = (sum(self.c.values())
                        + sum(v for v in config.get("criteres_supplementaires", {}).values()
                              if isinstance(v, (int, float)))
                        + 5)              # bonus « corridor éprouvé »
        self.facteurs = config["facteurs"]
        self.profil = profil or {}

    # ------------------------------------------------------------- marge --
    def _marge(self, opp) -> tuple[float, str, str]:
        """Calculable seulement si les coûts sont au profil. Sinon NON MESURÉE."""
        couts = self.profil.get("couts_exploitation") or {}
        requis = self.cfg_marge.get("calculable_si", [])
        manquants = [c for c in requis if not couts.get(c)]
        if manquants or not opp.montant or not opp.duree_mois:
            raison = ("coûts d'exploitation non renseignés au profil"
                      if manquants else "montant ou durée NON PUBLIÉS")
            return self.cfg_marge.get("points_si_non_mesuree", 5), raison, NON_MESUREE

        mois = max(opp.duree_mois, 1)
        recette = opp.montant / mois
        km_mois = (opp.km_annuels or 0) / 12
        depense = (km_mois * couts["cout_km"]
                   + (opp.chauffeurs_requis or 1) * 21 * couts["cout_chauffeur_jour"])
        marge = recette - depense
        taux = marge / recette if recette else 0
        pts = self.cfg_marge.get("points_si_bonne", 10) if taux >= 0.15 else 0
        return pts, f"marge estimée {taux:.0%} sur données publiées", \
               f"{marge:,.0f} €/mois ({taux:.0%})".replace(",", " ")

    # ------------------------------------------------------------ taille --
    def _taille(self, montant, duree_mois) -> tuple[float, str]:
        t = self.taille
        if not montant:
            return t["points_non_publie"], "montant NON PUBLIÉ — neutre, jamais pénalisant"
        if montant > t["hors_gabarit_au_dela"]:
            return t["points_hors_gabarit"], (
                f"{montant:,.0f} € — hors gabarit en titulaire direct".replace(",", " "))
        mensuel = montant / max(duree_mois or 12, 1)
        if t["mensuel_ideal_min"] <= mensuel <= t["mensuel_ideal_max"]:
            # DANS la cible, plus de récurrent mensuel vaut plus. Un forfait
            # unique donnait le même nombre de points à 8 000, 12 000 et
            # 15 000 €/mois : trois affaires très différentes ressortaient à
            # égalité, et le radar ne savait plus dire laquelle attaquer.
            #
            # La montée s'arrête au « confortable » du profil : au-delà, ce
            # n'est plus un meilleur contrat, c'est un contrat plus lourd —
            # d'où la cloche, et non une pente sans fin.
            confortable = t.get("mensuel_confortable", t["mensuel_ideal_max"])
            haut = max(confortable, t["mensuel_ideal_min"] + 1)
            part = min((mensuel - t["mensuel_ideal_min"])
                       / (haut - t["mensuel_ideal_min"]), 1.0)
            plancher = t.get("points_bas_de_cible", t["points_dans_la_cible"] * 0.6)
            points = plancher + (t["points_dans_la_cible"] - plancher) * part
            return round(points, 1), (
                f"{mensuel:,.0f} €/mois — dans la cible économique".replace(",", " "))
        if montant <= t["total_confortable_max"]:
            return t["points_proche"], f"{mensuel:,.0f} €/mois — proche de la cible".replace(",", " ")
        return t["points_hors_cible"], f"{montant:,.0f} € — au-dessus du confortable".replace(",", " ")

    def _palier_recurrence(self, cadence) -> tuple[float, str]:
        cle = (cadence or "inconnue").lower()
        libelle = {"quotidienne": "tournée quotidienne", "hebdomadaire": "flux hebdomadaire",
                   "mensuelle": "besoin mensuel", "pluriannuelle": "contrat pluriannuel",
                   "ponctuelle": "prestation ponctuelle"}.get(cle, "cadence NON PUBLIÉE")
        return self.rec.get(cle, self.rec["inconnue"]), libelle

    # ------------------------------------------------------------ calcul --
    def calculer(self, *, correspondance, zone, bilan, opp, type_opp: Type,
                 cadence=None, jours_restants=None) -> Score:
        L: list[Ligne] = []
        c, e = self.c, self.effort

        # 1. Sais-je faire ?
        #
        # On mesure si le besoin tombe DANS mon métier — pas combien de fois il
        # nomme mes métiers. L'ancienne règle donnait la moitié des points à une
        # famille et le plein à deux : un communiqué de presse bavard battait un
        # intitulé de marché précis, à besoin égal. C'était une prime à la
        # verbosité du texte, et elle avantageait mécaniquement les sources qui
        # écrivent long. « Distribution de colis » est parfaitement adéquat même
        # s'il ne cite qu'un seul de mes métiers.
        if correspondance.familles:
            preuves = [t for v in correspondance.preuves.values() for t in v][:2]
            libelles = ", ".join(correspondance.familles[:2])
            L.append(Ligne("adéquation opérationnelle", c["adequation_operationnelle"],
                           f"dans mon métier : {libelles}"
                           + (f" — « {preuves[0]} »" if preuves else "")))
        elif correspondance.domaine_transport:
            # Le domaine est confirmé, la spécialité non : adéquation partielle.
            L.append(Ligne("adéquation opérationnelle",
                           round(c["adequation_operationnelle"] * 0.5, 1),
                           f"domaine reconnu, spécialité NON IDENTIFIÉE"
                           f" — {correspondance.preuve_domaine or 'à confirmer'}"))
        elif type_opp is Type.A_CONSTRUIRE:
            L.append(Ligne("adéquation opérationnelle", c["adequation_operationnelle"] * 0.4,
                           "métier nouveau — adéquation partielle par les moyens"))
        else:
            L.append(Ligne("adéquation opérationnelle", 0, "aucune famille reconnue"))

        # 2. Accessibilité pour une PME récente
        #
        # Piège : une source qui ne publie AUCUNE exigence produit un bilan
        # vide, indistinguable d'un bilan « tout est couvert ». Récompenser ce
        # vide revenait à mieux noter une annonce muette qu'une annonce précise
        # — et à traiter NON MESURÉ comme un zéro favorable. Une opportunité
        # dont on ne sait rien n'est pas une opportunité facile : c'est une
        # opportunité qu'on n'a pas encore lue.
        # TROIS CAS, jamais confondus :
        #
        #   PUBLIÉE ET COUVERTE      → information positive, points pleins
        #   PUBLIÉE ET NON COUVERTE  → manque réel, points réduits ou nuls
        #   AUCUNE EXIGENCE PUBLIÉE  → NON MESURÉ, position neutre
        #
        # Absence d'information ≠ absence de difficulté. Le silence d'une
        # annonce ne rapporte aucun point : il ne prouve pas que le besoin est
        # facile, il prouve qu'on ne l'a pas encore lu.
        exigences_publiees = bool(opp.exigences or opp.chauffeurs_requis
                                  or opp.vehicules_requis or opp.exigences_texte)
        if not exigences_publiees:
            acces = c["accessibilite_pme"] * 0.5
            raison = "AUCUNE EXIGENCE PUBLIÉE — NON MESURÉ, ni bon ni mauvais"
        elif bilan.bloquants:
            acces = 0
            raison = f"PUBLIÉE ET NON COUVERTE — {bilan.bloquants[0][:44]}"
        elif bilan.mobilisations and bilan.a_verifier:
            acces = c["accessibilite_pme"] * 0.5
            raison = (f"PUBLIÉE, à mobiliser et {len(bilan.a_verifier)} point(s) "
                      f"À CONFIRMER")
        elif bilan.mobilisations:
            acces = c["accessibilite_pme"] * 0.8
            raison = "PUBLIÉE ET NON COUVERTE — accessible après mobilisation"
        elif bilan.a_verifier:
            acces = c["accessibilite_pme"] * 0.55
            raison = f"PUBLIÉE mais {len(bilan.a_verifier)} exigence(s) À CONFIRMER"
        else:
            acces = c["accessibilite_pme"]
            raison = "PUBLIÉE ET COUVERTE — exigences satisfaites en l'état"
        L.append(Ligne("accessibilité PME", round(acces, 1), raison))

        # 3. Géographie
        bareme = {Zone.CORRIDOR: 1.0, Zone.NATIONAL: 0.75, Zone.A_VERIFIER: 0.4,
                  Zone.HORS_ZONE: 0.0}
        L.append(Ligne("géographie", round(c["geographie"] * bareme[zone.zone], 1),
                       zone.raisons[0] if zone.raisons else zone.zone.value))
        if zone.corridor_eprouve:
            L.append(Ligne("corridor éprouvé", 5, "trajet déjà exécuté"))

        # 4. Proximité du dépôt — moins de route, plus de marge
        d = opp.distance_depot_km
        if d is None:
            L.append(Ligne("proximité", self.sup.get("proximite_depot", 10) * 0.5,
                           "distance au dépôt NON PUBLIÉE — neutre"))
        elif d <= e.get("distance_depot_confortable_km", 50):
            L.append(Ligne("proximité", self.sup.get("proximite_depot", 10),
                           f"{d:g} km du dépôt — tournée courte"))
        elif d <= e.get("distance_depot_lointaine_km", 150):
            L.append(Ligne("proximité", self.sup.get("proximite_depot", 10) * 0.4,
                           f"{d:g} km du dépôt"))
        else:
            L.append(Ligne("proximité", 0, f"{d:g} km du dépôt — éloigné"))

        # 5. Taille adaptée
        pts, raison = self._taille(opp.montant, opp.duree_mois)
        L.append(Ligne("taille adaptée", pts, raison))

        # 6. Récurrence
        pts, raison = self._palier_recurrence(cadence or opp.cadence)
        L.append(Ligne("récurrence", pts, raison))

        # 7. Démarrage — même règle : ne pas confondre « rien à mobiliser » et
        #    « on ne sait pas encore ce qu'il faudra mobiliser ».
        if bilan.mobilisations:
            L.append(Ligne("démarrage", round(c["rapidite_demarrage"] * 0.4, 1),
                           "conditionné à une location ou un recrutement"))
        elif not exigences_publiees:
            L.append(Ligne("démarrage", round(c["rapidite_demarrage"] * 0.5, 1),
                           "moyens nécessaires NON PUBLIÉS — à confirmer"))
        else:
            L.append(Ligne("démarrage", c["rapidite_demarrage"],
                           "exécutable avec les moyens en place"))

        # 8. Marge — calculée ou honnêtement NON MESURÉE
        pts, raison, marge = self._marge(opp)
        L.append(Ligne("marge", pts, raison))

        # 9. Effort : kilomètres et horaires
        if opp.km_annuels:
            if opp.km_annuels >= e.get("km_annuels_lourds", 60000):
                L.append(Ligne("kilométrage", self.pen["kilometrage_lourd"],
                               f"{opp.km_annuels:,.0f} km/an — usure et carburant".replace(",", " ")))
            elif opp.km_annuels <= e.get("km_annuels_confortables", 20000):
                L.append(Ligne("kilométrage", 4,
                               f"{opp.km_annuels:,.0f} km/an — tournée dense".replace(",", " ")))
        contraintes = [n for n, v in (("nuit", opp.travail_nuit),
                                      ("week-end", opp.travail_weekend)) if v]
        if contraintes:
            L.append(Ligne("horaires", self.pen["horaires_contraignants"],
                           "travail " + " et ".join(contraintes)))

        # 10. Investissement et risque
        if bilan.mobilisations:
            L.append(Ligne("investissement", self.pen["complexite_investissement"],
                           f"{len(bilan.mobilisations)} moyen(s) à mobiliser"))
        if type_opp is Type.A_CONSTRUIRE:
            L.append(Ligne("risque", self.pen["risque_operationnel"],
                           "montée en compétence sur un métier nouveau"))
        if bilan.a_verifier:
            L.append(Ligne("exigences non confirmées", self.pen["exigences_non_confirmees"],
                           f"{len(bilan.a_verifier)} point(s) à vérifier"))

        # 11. Concurrence probable
        indices = []
        if opp.montant and opp.montant >= self.conc["seuil_montant_gros_acteurs"]:
            indices.append(f"montant de {opp.montant:,.0f} €".replace(",", " "))
        exi = opp.exigences or {}
        if exi.get("chiffre_affaires_min", 0) >= self.conc["seuil_ca_exige"]:
            indices.append("chiffre d'affaires minimum élevé")
        if exi.get("anciennete_min_annees", 0) >= self.conc["seuil_anciennete_exigee"]:
            indices.append("ancienneté élevée exigée")
        if indices:
            L.append(Ligne("concurrence", self.pen["concurrence_grands_acteurs"],
                           "probablement disputé par de grands acteurs : " + ", ".join(indices)))

        total = sum(l.points for l in L)
        facteur = self.facteurs.get(type_opp.value, 1.0)
        if facteur != 1.0:
            total *= facteur
            L.append(Ligne("type", 0, f"{type_opp.value} — pondéré ×{facteur}"))
        # RAMENER À 100 PLUTÔT QUE COUPER À 100.
        #
        # Les critères plafonnaient à 100 sur une somme atteignable d'environ
        # 120 : tout ce qui dépassait était rogné, et les meilleures affaires
        # arrivaient à égalité. Un contrat à 8 000 €/mois, un à 12 000 et un à
        # 15 000 ressortaient tous à 100 — exactement là où le radar doit
        # trancher. On normalise donc au lieu de tronquer : l'ordre est
        # conservé, et 100 ne s'atteint que sur un cas réellement parfait.
        note = 100 * total / self.plafond if self.plafond else total
        return Score(max(0, min(100, round(note))), L, marge_estimee=marge)
