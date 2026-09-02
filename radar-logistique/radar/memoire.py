"""Mémoire des marchés attribués.

Un marché attribué aujourd'hui n'est PAS une opportunité — il ne sort jamais
dans les notifications. Mais il devient une opportunité datée : un contrat de
3 ans conclu en 2026 sera remis en concurrence vers 2029.

C'est le seul endroit du système qui produit une opportunité future à partir
d'un fait passé. Aucune source ne publie ce calendrier : il se calcule.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from .statut import parse_date

# Durée retenue quand l'avis ne la publie pas. Elle n'est PAS inventée dans les
# données : la date estimée est marquée comme telle et l'incertitude est portée.
DUREE_PAR_DEFAUT_MOIS = None


@dataclass
class Renouvellement:
    acheteur: str | None
    titulaire: str | None
    montant: float | None
    duree_mois: int | None
    prestation: str
    conclu_le: datetime | None
    remise_en_concurrence: datetime | None
    fiabilite: str          # "calculée" | "A_VERIFIER"
    commentaire: str


def memoriser(opp) -> Renouvellement:
    conclu, _ = parse_date(opp.attribue_le or opp.publie_le)
    duree = opp.duree_mois

    if conclu and duree:
        # Un marché se prépare en amont de son échéance : l'avis de
        # renouvellement paraît typiquement quelques mois avant la fin.
        echeance = conclu + timedelta(days=int(duree * 30.44))
        return Renouvellement(
            opp.acheteur, opp.titulaire, opp.montant, duree, opp.intitule, conclu, echeance,
            "calculée",
            f"contrat de {duree} mois conclu le {conclu:%d/%m/%Y} — "
            f"remise en concurrence attendue vers {echeance:%m/%Y}")

    manque = []
    if not conclu:
        manque.append("date de conclusion")
    if not duree:
        manque.append("durée")
    return Renouvellement(
        opp.acheteur, opp.titulaire, opp.montant, duree, opp.intitule, conclu, None,
        "A_VERIFIER",
        "échéance non calculable — " + " et ".join(manque) + " non publiée(s)")


def calendrier(renouvellements, dans_les_mois=18):
    """Ce qui va revenir sur le marché, trié par date. Sans date : à part."""
    maintenant = datetime.now(tz=None).replace(tzinfo=None)
    dates, sans_date = [], []
    for r in renouvellements:
        if r.remise_en_concurrence:
            reste = (r.remise_en_concurrence.replace(tzinfo=None) - maintenant).days
            if 0 <= reste <= dans_les_mois * 30:
                dates.append((reste, r))
        else:
            sans_date.append(r)
    dates.sort(key=lambda x: x[0])
    return [r for _, r in dates], sans_date
