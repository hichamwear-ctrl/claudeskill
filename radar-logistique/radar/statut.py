"""États de date. CHANGEMENT : quatre états au lieu de trois.

  🟢 OUVERT        échéance à venir
  🟠 BIENTOT_FERME échéance proche — moins de 7 jours
  🔴 DEPASSE       échéance passée : plus aucun dépôt possible
  🔵 ATTRIBUE      marché conclu : moteur DÉVELOPPER
  ⚪ INCONNUE      rien de publié — conservé et signalé, JAMAIS écarté

Règle absolue : aucune date n'est jamais inventée. Absente, illisible ou
contradictoire → INCONNUE.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from zoneinfo import ZoneInfo

BRUXELLES = ZoneInfo("Europe/Brussels")
JOURS_BIENTOT_FERME = 7


class Statut(Enum):
    OUVERT = "OUVERT"
    BIENTOT_FERME = "BIENTOT_FERME"
    DEPASSE = "DEPASSE"
    ATTRIBUE = "ATTRIBUE"
    INCONNUE = "INCONNUE"

    @property
    def emoji(self) -> str:
        return {"OUVERT": "🟢", "BIENTOT_FERME": "🟠", "DEPASSE": "🔴",
                "ATTRIBUE": "🔵", "INCONNUE": "⚪"}[self.value]

    @property
    def depot_possible(self) -> bool:
        """Une date inconnue n'interdit pas de déposer : elle interdit d'affirmer."""
        return self in (Statut.OUVERT, Statut.BIENTOT_FERME, Statut.INCONNUE)


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
    if valeur in (None, "", "None", "A_VERIFIER", "INCONNU"):
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
    """N'évalue que des FAITS DE DATE et de type d'avis. Le métier, la zone et
    les capacités sont jugés ailleurs : un fait ne s'interprète qu'à un endroit."""
    maintenant = maintenant or datetime.now(timezone.utc)
    cle = (opp.type_avis or "").strip().lower().replace("_", "-")

    if opp.attribue or cle in TYPES_ATTRIBUTION:
        return Verdict(Statut.ATTRIBUE, "marché déjà attribué",
                       bloquants=["marché déjà attribué"])

    dt, echec = parse_date(opp.echeance_brute)
    if dt is None:
        return Verdict(Statut.INCONNUE, "échéance NON PUBLIÉE",
                       a_verifier=[f"date limite : {echec} — à confirmer à la source"])

    reste = dt - maintenant
    if reste.total_seconds() <= 0:
        return Verdict(Statut.DEPASSE, f"clôturé le {dt:%d/%m/%Y à %H:%M}",
                       echeance=dt, jours_restants=reste.days,
                       bloquants=["date limite dépassée"])

    pub, _ = parse_date(opp.publie_le)
    if pub and pub > dt:
        return Verdict(Statut.INCONNUE, "dates contradictoires", echeance=dt,
                       jours_restants=reste.days,
                       a_verifier=["publication postérieure à la clôture — dates à confirmer"])

    if reste.days < JOURS_BIENTOT_FERME:
        return Verdict(Statut.BIENTOT_FERME, f"ferme le {dt:%d/%m/%Y à %H:%M}",
                       echeance=dt, jours_restants=reste.days,
                       a_verifier=[f"délai court : {reste.days} j pour monter le dossier"])
    return Verdict(Statut.OUVERT, f"ouvert jusqu'au {dt:%d/%m/%Y à %H:%M}",
                   echeance=dt, jours_restants=reste.days)
