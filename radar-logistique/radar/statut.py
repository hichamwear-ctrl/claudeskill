"""🟢 POSTULABLE · 🟠 A_VERIFIER · 🔴 NON_POSTULABLE

Règle absolue sur les dates : ne JAMAIS en inventer une. Absente, illisible ou
contradictoire → A_VERIFIER, jamais POSTULABLE et jamais NON_POSTULABLE.
Ne pas pouvoir confirmer qu'un marché est ouvert n'est pas la preuve qu'il est
fermé.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from zoneinfo import ZoneInfo

BRUXELLES = ZoneInfo("Europe/Brussels")


class Statut(Enum):
    POSTULABLE = "POSTULABLE"
    A_VERIFIER = "A_VERIFIER"
    NON_POSTULABLE = "NON_POSTULABLE"

    @property
    def emoji(self) -> str:
        return {"POSTULABLE": "🟢", "A_VERIFIER": "🟠", "NON_POSTULABLE": "🔴"}[self.value]

    @property
    def notifiable(self) -> bool:
        """Les 🔴 ne partent jamais comme opportunités."""
        return self is not Statut.NON_POSTULABLE


TYPES_ATTRIBUTION = {"attribution", "resultat", "avis-attribution", "award",
                     "contract-award", "resultat-marche", "gunning"}
TYPES_INFORMATIFS = {"information-prealable", "avis-preinformation", "prior-information",
                     "planification", "consultation-marche", "avis-informatif"}


@dataclass
class Verdict:
    statut: Statut
    motif: str
    echeance: datetime | None = None
    jours_restants: int | None = None
    a_verifier: list[str] = field(default_factory=list)
    bloquants: list[str] = field(default_factory=list)


def parse_date(valeur, defaut_tz=BRUXELLES) -> tuple[datetime | None, str | None]:
    """Renvoie (date, raison_d_echec). Aucune date de repli n'est jamais forgée."""
    if valeur in (None, "", "None", "A_VERIFIER"):
        return None, "aucune date publiée"
    if isinstance(valeur, datetime):
        return (valeur if valeur.tzinfo else valeur.replace(tzinfo=defaut_tz)), None
    texte = str(valeur).strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(texte)
    except ValueError:
        for fmt in ("%d/%m/%Y %H:%M", "%d/%m/%Y", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%Y%m%d"):
            try:
                dt = datetime.strptime(texte, fmt)
                break
            except ValueError:
                continue
        else:
            return None, f"date illisible ({valeur!r})"
    return (dt if dt.tzinfo else dt.replace(tzinfo=defaut_tz)), None


def evaluer(opp, *, zone_compatible=True, zone_raison="", activite_compatible=True,
            activite_raison="", eligibilite=None, maintenant=None) -> Verdict:
    """Combine les faits vérifiables. L'ordre compte : un marché attribué reste
    fermé même si sa date de clôture est future."""
    maintenant = maintenant or datetime.now(timezone.utc)
    a_verifier: list[str] = []
    cle = (opp.type_avis or "").strip().lower().replace("_", "-")

    # 1. Faits qui ferment définitivement.
    if opp.attribue or cle in TYPES_ATTRIBUTION:
        return Verdict(Statut.NON_POSTULABLE, "marché déjà attribué",
                       bloquants=["marché déjà attribué"])
    if cle in TYPES_INFORMATIFS:
        return Verdict(Statut.NON_POSTULABLE, "avis informatif — aucun dépôt attendu",
                       bloquants=["avis purement informatif"])
    if not activite_compatible:
        return Verdict(Statut.NON_POSTULABLE, activite_raison or "activité incompatible",
                       bloquants=[activite_raison or "activité incompatible"])
    if not zone_compatible:
        return Verdict(Statut.NON_POSTULABLE, zone_raison or "zone incompatible",
                       bloquants=[zone_raison or "zone incompatible"])
    if eligibilite is not None and eligibilite.bloquants:
        return Verdict(Statut.NON_POSTULABLE,
                       "exigence obligatoire impossible à remplir",
                       bloquants=list(eligibilite.bloquants))

    # 2. La date.
    dt, echec = parse_date(opp.echeance_brute)
    if dt is None:
        a_verifier.append(f"date limite : {echec} — à confirmer sur la plateforme")
        statut = Statut.A_VERIFIER
        jours = None
        motif = "échéance non confirmée"
    else:
        reste = dt - maintenant
        jours = reste.days
        if reste.total_seconds() <= 0:
            return Verdict(Statut.NON_POSTULABLE, f"clôturé le {dt:%d/%m/%Y à %H:%M}",
                           echeance=dt, jours_restants=jours,
                           bloquants=["date limite dépassée"])
        # Contradiction : publié après la clôture -> on ne tranche pas.
        pub, _ = parse_date(opp.publie_le)
        if pub and pub > dt:
            a_verifier.append("dates contradictoires (publication postérieure à la clôture)")
            statut = Statut.A_VERIFIER
            motif = "dates contradictoires"
        else:
            statut = Statut.POSTULABLE
            motif = f"ouvert jusqu'au {dt:%d/%m/%Y à %H:%M}"

    # 3. Ce qui n'empêche pas de déposer mais doit être vérifié.
    if eligibilite is not None and eligibilite.a_verifier:
        a_verifier += eligibilite.a_verifier
        if statut is Statut.POSTULABLE:
            statut = Statut.A_VERIFIER
            motif += " — points à vérifier"

    return Verdict(statut, motif, echeance=dt, jours_restants=jours, a_verifier=a_verifier)
