"""« Est-ce que je peux encore postuler aujourd'hui ? »

C'est le seul critère qui écarte une annonce. Tout le reste trie et annote.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from zoneinfo import ZoneInfo

BRUXELLES = ZoneInfo("Europe/Brussels")

# Un avis clôturant dans moins de N jours reste ACTIONNABLE — il est simplement
# signalé comme tendu. Ce n'est pas au bot de décider que c'est trop court.
URGENCE_JOURS = 7


class Statut(Enum):
    OUVERT = "ouvert"
    ECHEANCE_INCONNUE = "echeance_inconnue"   # livré, signalé — jamais écarté
    CLOTURE = "cloture"
    ATTRIBUE = "attribue"
    INFORMATIF = "informatif"

    @property
    def actionnable(self) -> bool:
        """Seuls ces deux états atteignent l'exploitant."""
        return self in (Statut.OUVERT, Statut.ECHEANCE_INCONNUE)


# Familles d'avis qui ne sont jamais des opportunités de dépôt.
TYPES_ATTRIBUTION = {
    "attribution", "resultat", "avis-attribution", "award",
    "contract-award", "resultat-marche",
}
TYPES_INFORMATIFS = {
    "information-prealable", "avis-preinformation", "prior-information",
    "avis-informatif", "planification", "consultation-marche",
    "rectificatif-sans-echeance",
}


@dataclass
class Verdict:
    statut: Statut
    motif: str
    echeance: datetime | None = None
    jours_restants: int | None = None
    urgent: bool = False
    signalements: list[str] = field(default_factory=list)

    @property
    def actionnable(self) -> bool:
        return self.statut.actionnable


def _maintenant() -> datetime:
    return datetime.now(timezone.utc)


def parse_echeance(valeur, defaut_tz=BRUXELLES) -> tuple[datetime | None, str | None]:
    """Renvoie (date_limite, raison_de_l_echec).

    Une date illisible renvoie None et une raison — JAMAIS une date de repli.
    Une date inventée ici ferait disparaître un marché ouvert, ou en ferait
    apparaître un clôturé comme déposable.
    """
    if valeur in (None, "", "None"):
        return None, "aucune date de clôture publiée"
    if isinstance(valeur, datetime):
        dt = valeur
    else:
        texte = str(valeur).strip().replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(texte)
        except ValueError:
            for fmt in ("%d/%m/%Y %H:%M", "%d/%m/%Y", "%Y-%m-%d %H:%M", "%Y%m%d"):
                try:
                    dt = datetime.strptime(texte, fmt)
                    break
                except ValueError:
                    continue
            else:
                return None, f"date de clôture illisible ({valeur!r})"
    if dt.tzinfo is None:
        # Une heure sans fuseau est locale au pouvoir adjudicateur.
        dt = dt.replace(tzinfo=defaut_tz)
    return dt, None


def evaluer(*, type_avis=None, echeance=None, deja_attribue=False,
            maintenant: datetime | None = None) -> Verdict:
    """Décide si l'annonce est encore déposable.

    L'ordre compte : un avis d'attribution reste une attribution même s'il
    porte une date future, et un marché attribué n'est plus déposable même si
    la date de clôture n'est pas encore passée.
    """
    maintenant = maintenant or _maintenant()
    signalements: list[str] = []
    cle = (type_avis or "").strip().lower().replace("_", "-")

    if deja_attribue or cle in TYPES_ATTRIBUTION:
        return Verdict(Statut.ATTRIBUE, "marché déjà attribué — dépôt impossible")

    if cle in TYPES_INFORMATIFS:
        return Verdict(Statut.INFORMATIF, "avis informatif — aucun dépôt attendu")

    dt, echec = parse_echeance(echeance)

    if dt is None:
        # Cas dangereux : ne JAMAIS écarter. Le coût d'un faux « clôturé »
        # est un contrat perdu ; celui d'un faux « ouvert », trente secondes.
        signalements.append(f"échéance à vérifier sur la plateforme — {echec}")
        return Verdict(Statut.ECHEANCE_INCONNUE,
                       "échéance non déterminable — livré par précaution",
                       signalements=signalements)

    restant = dt - maintenant
    jours = restant.days if restant.total_seconds() >= 0 else -((-restant).days + 1)

    if restant.total_seconds() <= 0:
        return Verdict(Statut.CLOTURE, f"clôturé le {dt:%d/%m/%Y à %H:%M}",
                       echeance=dt, jours_restants=jours)

    urgent = restant.days < URGENCE_JOURS
    if urgent:
        signalements.append(f"délai court : {restant.days} j pour monter le dossier")
    return Verdict(Statut.OUVERT, f"ouvert jusqu'au {dt:%d/%m/%Y à %H:%M}",
                   echeance=dt, jours_restants=restant.days,
                   urgent=urgent, signalements=signalements)
