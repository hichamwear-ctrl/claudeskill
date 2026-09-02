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


def evaluer(opp, *, maintenant=None) -> Verdict:
    """N'évalue plus que des FAITS DE DATE et de type d'avis.

    La compatibilité métier, la zone et les capacités sont jugées ailleurs, et
    c'est classification.py qui recompose le tout : un même fait ne doit être
    interprété qu'à un seul endroit.
    """
    maintenant = maintenant or datetime.now(timezone.utc)
    cle = (opp.type_avis or "").strip().lower().replace("_", "-")

    if opp.attribue or cle in TYPES_ATTRIBUTION:
        return Verdict(Statut.NON_POSTULABLE, "marché déjà attribué",
                       bloquants=["marché déjà attribué"])
    if cle in TYPES_INFORMATIFS:
        return Verdict(Statut.NON_POSTULABLE, "avis informatif — aucun dépôt attendu",
                       bloquants=["avis purement informatif"])

    dt, echec = parse_date(opp.echeance_brute)
    if dt is None:
        # Ne JAMAIS écarter sur une date illisible : rater un marché ouvert coûte
        # un contrat, recevoir un marché clos coûte trente secondes.
        return Verdict(Statut.A_VERIFIER, "échéance non confirmée",
                       a_verifier=[f"date limite : {echec} — à confirmer sur la plateforme"])

    reste = dt - maintenant
    if reste.total_seconds() <= 0:
        return Verdict(Statut.NON_POSTULABLE, f"clôturé le {dt:%d/%m/%Y à %H:%M}",
                       echeance=dt, jours_restants=reste.days,
                       bloquants=["date limite dépassée"])

    pub, _ = parse_date(opp.publie_le)
    if pub and pub > dt:
        return Verdict(Statut.A_VERIFIER, "dates contradictoires", echeance=dt,
                       jours_restants=reste.days,
                       a_verifier=["publication postérieure à la clôture — dates à confirmer"])

    a_verifier = []
    if reste.days < 7:
        a_verifier.append(f"délai court : {reste.days} j pour monter le dossier")
    return Verdict(Statut.POSTULABLE, f"ouvert jusqu'au {dt:%d/%m/%Y à %H:%M}",
                   echeance=dt, jours_restants=reste.days, a_verifier=a_verifier)
