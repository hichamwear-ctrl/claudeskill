"""CA PUBLIÉ · CA ESTIMABLE · CA INCONNU — trois états, jamais confondus.

Un montant absent n'est ni un zéro, ni un bonus. C'est un TROU, et un trou se
nomme. Trois états seulement :

    PUBLIÉ      la source donne un montant. On le lit, on le ramène au mois.
    ESTIMABLE   la source ne donne pas de montant, mais elle donne de quoi
                l'encadrer — un nombre de véhicules, une cadence, un
                kilométrage — ET le profil déclare une base de calcul observée.
                On rend une FOURCHETTE, avec la méthode écrite.
    INCONNU     ni l'un ni l'autre. On l'écrit, et on demande.

La règle qui gouverne ESTIMABLE : **aucune estimation sans base déclarée au
profil**. Sans `references_economiques`, ce module ne fabrique aucun chiffre —
il rend INCONNU en disant pourquoi. Une fourchette inventée est pire qu'un
trou : un trou se voit, une fourchette inventée se croit.

La marge suit la même règle et vit dans score.py : NON MESURÉE tant que les
coûts d'exploitation réels ne sont pas au profil.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Etat(Enum):
    PUBLIE = "PUBLIÉ"
    ESTIMABLE = "ESTIMATION"
    INCONNU = "NON PUBLIÉ"


@dataclass
class CA:
    etat: Etat
    mensuel: float | None = None          # le point central, quand il existe
    bas: float | None = None              # borne basse d'une estimation
    haut: float | None = None
    methode: str = ""                     # d'où vient l'estimation, en clair
    manque: str = ""                      # ce qu'il faudrait pour mesurer

    @property
    def mesurable(self) -> bool:
        return self.etat is not Etat.INCONNU

    def ligne(self) -> str:
        """Ce qui s'écrit sur une fiche. Jamais un nombre nu sans son état."""
        if self.etat is Etat.PUBLIE:
            return f"{self.mensuel:,.0f} €/mois — PUBLIÉ".replace(",", " ")
        if self.etat is Etat.ESTIMABLE:
            # Pas de rstrip ici : « 10.5 » arrondi à « 10 » puis dépouillé de
            # son zéro devenait « 1 ». Une fourchette fausse d'un facteur dix
            # est pire qu'une absence de fourchette.
            def k(v):
                return f"{v / 1000:.0f}" if v >= 10000 else f"{v / 1000:.1f}"
            return f"~{k(self.bas)}–{k(self.haut)} k€/mois — ESTIMATION"
        return "NON PUBLIÉ → IMPOSSIBLE À MESURER"

    def detail(self) -> list[str]:
        if self.etat is Etat.ESTIMABLE and self.methode:
            return [f"MÉTHODE : {self.methode}"]
        if self.etat is Etat.INCONNU and self.manque:
            return [f"À DEMANDER : {self.manque}"]
        return []


# Combien de fois par mois une cadence se produit. Sert UNIQUEMENT quand la
# source déclare que son montant est un prix récurrent, jamais par défaut.
OCCURRENCES_PAR_MOIS = {
    "quotidienne": 21.0,      # jours ouvrés
    "hebdomadaire": 4.33,
    "bimensuelle": 2.0,
    "mensuelle": 1.0,
}


def mesurer(opp, profil: dict | None = None) -> CA:
    """Lit le CA mensuel. N'invente jamais un chiffre."""
    montant = getattr(opp, "montant", None)
    if montant:
        # L'UNITÉ DU MONTANT SE DÉCLARE, elle ne se devine pas.
        #
        # Le montant était toujours traité comme un TOTAL réparti sur la durée,
        # avec 12 mois par défaut. Sur une bourse de fret, « 4 200 € » est un
        # prix par tournée, pas un contrat annuel : l'affaire ressortait à
        # 350 €/mois au lieu de ~18 000. L'erreur allait dans le sens qui fait
        # RATER une bonne affaire — la pire des deux directions.
        unite = (getattr(opp, "montant_unite", None) or "total").lower()
        cadence = (getattr(opp, "cadence", None) or "").lower()
        if unite in ("par_periode", "recurrent", "par_tournee"):
            par_mois = OCCURRENCES_PAR_MOIS.get(cadence)
            if par_mois:
                return CA(Etat.PUBLIE, mensuel=montant * par_mois)
            # Prix récurrent sans cadence lisible : on ne devine pas la
            # fréquence. Le montant est publié, sa périodicité ne l'est pas.
            return CA(Etat.INCONNU,
                      manque=f"prix récurrent publié ({montant:,.0f} €) mais "
                             "cadence NON PUBLIÉE — combien de fois par mois ?"
                             .replace(",", " "))
        duree = max(getattr(opp, "duree_mois", None) or 12, 1)
        return CA(Etat.PUBLIE, mensuel=montant / duree)

    # ── ESTIMABLE : seulement si le profil déclare une base OBSERVÉE ──────
    refs = ((profil or {}).get("references_economiques") or {})
    base_vehicule = refs.get("ca_mensuel_par_vehicule")
    base_km = refs.get("ca_par_km")
    marge_erreur = refs.get("marge_erreur", 0.25)

    vehicules = getattr(opp, "vehicules_requis", None)
    km = getattr(opp, "km_annuels", None)

    if base_vehicule and vehicules:
        centre = float(base_vehicule) * int(vehicules)
        return CA(Etat.ESTIMABLE, mensuel=centre,
                  bas=centre * (1 - marge_erreur), haut=centre * (1 + marge_erreur),
                  methode=f"{vehicules} véhicule(s) × {base_vehicule:,.0f} €/mois "
                          f"observés au profil, ±{marge_erreur:.0%}".replace(",", " "))
    if base_km and km:
        centre = float(base_km) * float(km) / 12
        return CA(Etat.ESTIMABLE, mensuel=centre,
                  bas=centre * (1 - marge_erreur), haut=centre * (1 + marge_erreur),
                  methode=f"{km:,.0f} km/an × {base_km} €/km observés au profil, "
                          f"±{marge_erreur:.0%}".replace(",", " "))

    # ── INCONNU : et on dit ce qui manque pour sortir de l'inconnu ────────
    if vehicules or km or getattr(opp, "cadence", None):
        manque = ("aucune base d'estimation au profil — renseigner "
                  "`references_economiques.ca_mensuel_par_vehicule` ou "
                  "`ca_par_km` à partir de contrats déjà réalisés")
    else:
        manque = "quel volume mensuel, ou quel budget ?"
    return CA(Etat.INCONNU, manque=manque)
