"""ADÉQUATION ≠ POTENTIEL. Deux questions, deux nombres, jamais écrasés en un.

Ce que le barème mesure — et il le dit lui-même, `taille_adaptee` vaut « à ma
capacité, PAS au montant le plus élevé » — c'est l'ADÉQUATION : est-ce mon
métier, est-ce à ma portée, est-ce dans ma zone, puis-je démarrer ?

Ce qu'il ne mesure pas, et ne doit pas mesurer : COMBIEN ÇA RAPPORTE.

Mesuré, chiffres à l'appui, sur des affaires identiques en tout sauf le CA :

    8 000 €/mois → 83      25 000 €/mois → 87
   12 000 €/mois → 84      40 000 €/mois → 87
   15 000 €/mois → 84     100 000 €/mois → 64  (pénalisé, hors gabarit)

12 000 et 15 000 €/mois sont à égalité : 108 000 € d'écart invisibles.
25 000 et 40 000 €/mois sont à égalité : 540 000 € d'écart invisibles.
Au-delà de 25 000 €/mois, AUCUN montant ne fait gagner un point — testé
jusqu'à 4,8 M€/an. Et il faut environ 45 000 €/an d'écart pour en gagner UN
seul en dessous de ce seuil.

Un score d'adéquation est le bon outil pour dire « puis-je le faire ». C'est
le mauvais outil pour dire « par quoi je commence ». Ce module ne retouche
aucun poids : il rend au CA son rang de dimension à part entière, et écrit
noir sur blanc pourquoi une affaire passe devant une autre.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .chiffre_affaires import Etat as EtatCA


@dataclass
class Priorite:
    """Pourquoi cette affaire est à cette place. Lisible ligne par ligne."""
    rang_ca: float = 0.0          # €/an, 0 quand non mesurable
    adequation: int = 0           # le score, tel quel
    ca_mesurable: bool = False
    intensite: float | None = None      # €/an par véhicule exigé
    couverture: float | None = None     # part du besoin couverte, 0–1
    explication: list = field(default_factory=list)

    @property
    def cle_de_tri(self) -> tuple:
        """Les affaires CHIFFRÉES d'abord, par CA décroissant ; les autres
        ensuite, par adéquation. Une affaire non chiffrée n'est pas moins
        bonne — elle est moins DÉCIDABLE, et se traite en appelant."""
        return (0 if self.ca_mesurable else 1,
                -self.rang_ca, -self.adequation)

    def ligne(self) -> str:
        return " · ".join(self.explication) or "aucun élément de priorité"


def _annuel(ca) -> float | None:
    if ca is None or ca.mensuel is None:
        return None
    return ca.mensuel * 12


def evaluer(ca, score, bilan, classement, opp) -> Priorite:
    """Assemble les deux dimensions, et dit ce qui départage."""
    annuel = _annuel(ca)
    p = Priorite(rang_ca=annuel or 0.0, adequation=score.total,
                 ca_mesurable=bool(annuel) and ca.etat is not EtatCA.INCONNU,
                 couverture=bilan.part_couverte())

    # 1. Ce que ça rapporte — et à quel titre.
    if ca is None or ca.etat is EtatCA.INCONNU:
        p.explication.append("CA NON MESURABLE — se décide en appelant, pas en lisant")
    elif ca.etat is EtatCA.ESTIMABLE:
        p.explication.append(f"CA ESTIMÉ {annuel:,.0f} €/an — fourchette, pas un fait"
                             .replace(",", " "))
    else:
        p.explication.append(f"CA PUBLIÉ {annuel:,.0f} €/an".replace(",", " "))

    # 2. Ce que ça coûte en capacité. « Beaucoup de CA » et « beaucoup de CA
    #    pour ce que ça consomme » sont deux choses différentes : 500 000 €
    #    avec vingt véhicules peut valoir moins que 150 000 € avec trois.
    vehicules = (opp.exigences or {}).get("vehicules_min") or opp.vehicules_requis
    if annuel and vehicules:
        p.intensite = annuel / int(vehicules)
        p.explication.append(
            f"{p.intensite:,.0f} €/an par véhicule exigé".replace(",", " "))


    # 3. Ce qu'il faut pour l'exécuter.
    if bilan.bloquants:
        part = f"{p.couverture:.0%}" if p.couverture is not None else "part inconnue"
        p.explication.append(f"couvre {part} du besoin — renfort obligatoire")
    elif bilan.mobilisations:
        p.explication.append("faisable après mobilisation")
    elif bilan.atouts:
        p.explication.append("faisable en l'état")
    else:
        p.explication.append("capacité nécessaire NON PUBLIÉE — "
                             "ni l'intensité ni la faisabilité ne sont mesurables")

    # 4. L'adéquation, en dernier — c'est un filtre, pas un classement.
    p.explication.append(f"adéquation {score.total}/100"
                         + ("" if score.mesurable else " — NON MESURABLE"))
    return p


@dataclass
class Couverture:
    """§12 — « 12 opportunités détectées » ≠ « 12 opportunités valorisées »."""
    publie_annuel: float = 0.0
    estime_annuel: float = 0.0
    n_publie: int = 0
    n_estime: int = 0
    n_non_mesurable: int = 0
    n_a_verifier: int = 0
    total: int = 0

    def ajouter(self, ca, a_verifier: bool = False) -> None:
        self.total += 1
        if a_verifier:
            self.n_a_verifier += 1
        annuel = _annuel(ca) or 0.0
        if ca is None or ca.etat is EtatCA.INCONNU:
            self.n_non_mesurable += 1
        elif ca.etat is EtatCA.ESTIMABLE:
            self.estime_annuel += annuel
            self.n_estime += 1
        else:
            self.publie_annuel += annuel
            self.n_publie += 1

    def rendu(self) -> list[str]:
        def e(v):
            return f"{v:,.0f} €/an".replace(",", " ")
        L = ["POTENTIEL COMMERCIAL", ""]
        L.append(f"  MESURÉ         {e(self.publie_annuel):>16}   "
                 f"sur {self.n_publie} affaire(s) — montant publié")
        L.append(f"  ESTIMABLE      {e(self.estime_annuel):>16}   "
                 f"sur {self.n_estime} affaire(s) — fourchette, pas un fait")
        L.append(f"  NON MESURABLE  {'—':>16}   "
                 f"{self.n_non_mesurable} affaire(s) — à demander au client")
        L.append("")
        L.append(f"  {self.total} opportunité(s) détectée(s), "
                 f"{self.n_publie + self.n_estime} réellement valorisée(s), "
                 f"{self.n_a_verifier} à vérifier.")
        L.append("  « détectée » ne veut pas dire « valorisée » : les trois lignes")
        L.append("  ci-dessus ne s'additionnent pas en un chiffre unique.")
        return L
