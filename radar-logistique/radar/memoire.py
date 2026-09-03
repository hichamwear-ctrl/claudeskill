"""Mémoire des marchés attribués — le moteur DÉVELOPPER.

Un marché attribué n'est pas une opportunité perdue : c'est une entreprise qui
vient de gagner du travail et qui devra l'exécuter. Elle aura peut-être besoin
de bras, et le marché reviendra un jour.

Rien n'est estimé ici : sans durée publiée, l'échéance n'est pas calculée, elle
est marquée A_VERIFIER.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

from .statut import parse_date


@dataclass
class Attribution:
    acheteur: str | None
    titulaire: str | None
    montant: float | None
    duree_mois: int | None
    prestation: str
    zone: str | None = None
    lots: list = field(default_factory=list)
    conclu_le: object = None
    debut: object = None
    fin: object = None
    remise_en_concurrence: object = None
    fiabilite: str = "A_VERIFIER"
    commentaire: str = ""
    contact: str | None = None
    sous_traitants: list = field(default_factory=list)
    taille_apparente: str = "A_VERIFIER"
    besoin_sous_traitance: str = "A_VERIFIER"

    # Compatibilité avec l'ancien nom du champ.
    @property
    def renouvellement(self):
        return self.remise_en_concurrence


def estimer_taille(titulaire: str | None, montant: float | None,
                   vehicules_connus: int | None = None) -> tuple[str, str]:
    """Taille apparente du titulaire, et probabilité qu'il sous-traite.

    Fondée uniquement sur ce qui est publié. Sans montant, on ne conclut rien —
    on ne devine pas la taille d'une entreprise.
    """
    if vehicules_connus:
        return (f"{vehicules_connus} véhicules connus",
                "probable" if vehicules_connus < 20 else "A_VERIFIER")
    if not montant:
        return "A_VERIFIER", "A_VERIFIER"
    if montant >= 5_000_000:
        return ("grand opérateur au vu du montant",
                "probable — un marché de cette taille se sous-traite en partie")
    if montant >= 1_000_000:
        return ("opérateur de taille moyenne à grande",
                "probable sur les zones périphériques")
    return ("taille non déterminable depuis le montant seul", "A_VERIFIER")


def memoriser(opp) -> Attribution:
    conclu, _ = parse_date(opp.attribue_le or opp.publie_le)
    debut, _ = parse_date(opp.date_demarrage)
    duree = opp.duree_mois
    zone = " → ".join(filter(None, ["/".join(opp.pays_collecte),
                                    "/".join(opp.pays_livraison)])) or opp.lieu_texte

    taille, besoin = estimer_taille(opp.titulaire, opp.montant)
    a = Attribution(
        acheteur=opp.acheteur, titulaire=opp.titulaire, montant=opp.montant,
        duree_mois=duree, prestation=opp.intitule, zone=zone,
        lots=[l.libelle if hasattr(l, "libelle") else str(l) for l in (opp.lots or [])],
        conclu_le=conclu, debut=debut, contact=opp.contact,
        taille_apparente=taille, besoin_sous_traitance=besoin)

    depart = debut or conclu
    if depart and duree:
        a.fin = depart + timedelta(days=int(duree * 30.44))
        a.remise_en_concurrence = a.fin
        a.fiabilite = "calculée"
        a.commentaire = (f"contrat de {duree} mois démarré le {depart:%d/%m/%Y} — "
                         f"fin vers {a.fin:%m/%Y}, remise en concurrence attendue avant")
        return a

    manque = [n for n, v in (("date de conclusion", depart), ("durée", duree)) if not v]
    a.commentaire = "échéance non calculable — " + " et ".join(manque) + " NON PUBLIÉE(S)"
    return a


def calendrier(attributions, dans_les_mois=24):
    """Ce qui va revenir sur le marché, trié. Sans date : à part, jamais estimé."""
    from datetime import datetime, timezone
    maintenant = datetime.now(timezone.utc)
    dates, sans_date = [], []
    for a in attributions:
        d = a.remise_en_concurrence
        if d:
            if d.tzinfo is None:
                d = d.replace(tzinfo=timezone.utc)
            reste = (d - maintenant).days
            if -30 <= reste <= dans_les_mois * 30:
                dates.append((reste, a))
        else:
            sans_date.append(a)
    dates.sort(key=lambda x: x[0])
    return [a for _, a in dates], sans_date
